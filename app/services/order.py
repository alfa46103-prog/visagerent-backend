# Файл: app/services/order.py
# Назначение: Сервис заказов.
#
# Заказ создаётся из корзины. Процесс:
#   1. Берём все CartItem пользователя
#   2. Создаём Order + OrderItem для каждого элемента
#   3. Конвертируем резервы в продажу (уменьшаем quantity на складе)
#   4. Записываем историю статусов
#   5. Очищаем корзину
#
# Статусная модель:
#   pending → confirmed → processing → ready → completed
#                                            → cancelled
#                                            → refunded

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.order import Order, OrderStatus, DeliveryType
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.cart_item import CartItem
from app.models.stock import Stock
from app.models.inventory_move import InventoryMove, MoveType
from app.models.user_point_session import UserPointSession
from app.schemas import OrderCreate, OrderStatusChange
from app.services.cart import clear_cart
from app.services.notification import enqueue_notification

from app.models.organization_user import OrganizationUser


# Допустимые переходы между статусами
# Ключ — текущий статус, значение — список статусов, в которые можно перейти
ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.READY, OrderStatus.CANCELLED],
    OrderStatus.READY: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
    OrderStatus.COMPLETED: [OrderStatus.REFUNDED],
    OrderStatus.CANCELLED: [],       # из отменённого никуда
    OrderStatus.REFUNDED: [],        # из возврата никуда
}


async def get_orders(
    db: AsyncSession,
    org_id: int,
    status: str | None = None,
    point_id: int | None = None,
    org_user_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Order]:
    """
    Список заказов организации с фильтрацией.

    Доступен сотрудникам через админку.
    Подгружаем items сразу, чтобы не было N+1 проблемы.
    """
    stmt = (
        select(Order)
        .where(Order.org_id == org_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if status:
        stmt = stmt.where(Order.status == status)
    if point_id:
        stmt = stmt.where(Order.point_id == point_id)
    if org_user_id:
        stmt = stmt.where(Order.org_user_id == org_user_id)

    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def get_order_by_id(
    db: AsyncSession,
    order_id: int,
    org_id: int,
) -> Order:
    """Получить заказ по ID с позициями."""
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.org_id == org_id)
        .options(selectinload(Order.items))
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def change_order_status(
    db: AsyncSession,
    order_id: int,
    org_id: int,
    data: OrderStatusChange,
    changed_by: int | None = None,
) -> Order:
    """
    Сменить статус заказа.

    Проверяет допустимость перехода по ALLOWED_TRANSITIONS.
    Записывает изменение в историю.

    При выполнении заказа:
      - начисляет баллы лояльности
      - обновляет total_orders_amount покупателя
      - пересчитывает уровень покупателя

    При отмене/возврате:
      - возвращает товары на склад
      - отзывает начисленные баллы
    """
    order = await get_order_by_id(db, order_id, org_id)

    # Проверяем допустимость нового статуса
    try:
        new_status = OrderStatus(data.new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change from '{order.status.value}' to '{new_status.value}'. "
                   f"Allowed: {[s.value for s in allowed]}",
        )

    old_status = order.status
    order.status = new_status

    # Если заказ отменён — возвращаем товары на склад
    if new_status == OrderStatus.CANCELLED:
        for item in order.items:
            stock_stmt = select(Stock).where(
                Stock.product_variant_id == item.product_variant_id,
                Stock.point_id == order.point_id,
            )
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()

            if stock:
                stock.quantity += item.quantity

                # Записываем движение: возврат
                move = InventoryMove(
                    org_id=org_id,
                    product_variant_id=item.product_variant_id,
                    to_point_id=order.point_id,
                    move_type=MoveType.RETURN,
                    quantity=item.quantity,
                    reference_id=order.id,
                    reference_type="order",
                    notes=f"Order cancelled: {data.comment or ''}",
                )
                db.add(move)

    # Если заказ выполнен — начисляем баллы и обновляем уровень
    if new_status == OrderStatus.COMPLETED:
        from app.services.loyalty import accrue_points_for_order, recalculate_user_tier, process_referral_bonus

        # Обновляем total_orders_amount у покупателя
        user = await db.get(OrganizationUser, order.org_user_id)
        if user:
            user.total_orders_amount = float(user.total_orders_amount) + float(order.total_price)

        # Начисляем баллы
        await accrue_points_for_order(
            db, org_id, order.org_user_id, order.id, float(order.total_price),
        )

        # Пересчитываем уровень покупателя
        await recalculate_user_tier(db, order.org_user_id, org_id)
        # Начисляем реферальный бонус (если первый заказ приглашённого)
        await process_referral_bonus(db, org_id, order.org_user_id, order.id)

    # Если отмена или возврат — забираем баллы обратно
    if new_status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        from app.services.loyalty import revoke_points_for_order

        await revoke_points_for_order(db, org_id, order.org_user_id, order.id)

    # Записываем в историю
    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        comment=data.comment,
    )
    db.add(history)

    await db.commit()
    return await get_order_by_id(db, order.id, org_id)


async def change_order_status(
    db: AsyncSession,
    order_id: int,
    org_id: int,
    data: OrderStatusChange,
    changed_by: int | None = None,
) -> Order:
    """
    Сменить статус заказа.

    Проверяет допустимость перехода по ALLOWED_TRANSITIONS.
    Записывает изменение в историю.

    При отмене — возвращает товары на склад.
    """
    order = await get_order_by_id(db, order_id, org_id)

    # Проверяем допустимость нового статуса
    try:
        new_status = OrderStatus(data.new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change from '{order.status.value}' to '{new_status.value}'. "
                   f"Allowed: {[s.value for s in allowed]}",
        )

    old_status = order.status
    order.status = new_status

    # Если заказ отменён — возвращаем товары на склад
    if new_status == OrderStatus.CANCELLED:
        for item in order.items:
            stock_stmt = select(Stock).where(
                Stock.product_variant_id == item.product_variant_id,
                Stock.point_id == order.point_id,
            )
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()

            if stock:
                stock.quantity += item.quantity

                # Записываем движение: возврат
                move = InventoryMove(
                    org_id=org_id,
                    product_variant_id=item.product_variant_id,
                    to_point_id=order.point_id,
                    move_type=MoveType.RETURN,
                    quantity=item.quantity,
                    reference_id=order.id,
                    reference_type="order",
                    notes=f"Order cancelled: {data.comment or ''}",
                )
                db.add(move)
    # Ставим уведомление в очередь для покупателя
    

    # Маппинг статусов на типы уведомлений
    status_notification_map = {
        OrderStatus.CONFIRMED: "order_confirmed",
        OrderStatus.CANCELLED: "order_cancelled",
        OrderStatus.COMPLETED: "order_confirmed",  # можно добавить order_completed шаблон
        OrderStatus.READY: "order_confirmed",
    }
    notif_type = status_notification_map.get(new_status)
    if notif_type:
        await enqueue_notification(
            db,
            org_id=org_id,
            org_user_id=order.org_user_id,
            notification_type=notif_type,
            payload={
                "order_id": order.order_id,
                "status": new_status.value,
                "total": str(order.total_price),
            },
        )
    # Записываем в историю
    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        comment=data.comment,
    )
    db.add(history)

    await db.commit()
    return await get_order_by_id(db, order.id, org_id)


async def get_order_history(
    db: AsyncSession,
    order_id: int,
    org_id: int,
) -> list[OrderStatusHistory]:
    """Получить историю статусов заказа."""
    # Проверяем что заказ наш
    await get_order_by_id(db, order_id, org_id)

    stmt = (
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.changed_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())