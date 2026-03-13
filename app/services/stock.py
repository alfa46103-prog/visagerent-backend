# Файл: app/services/stock.py
# Назначение: Сервис для управления складскими остатками.
#
# Остаток (Stock) — запись "на точке X варианта Y лежит N штук".
# Для каждой пары (вариант, точка) ровно одна запись.
#
# Движение (InventoryMove) — история всех изменений остатков.
# Каждая корректировка, продажа, возврат фиксируется как движение.
#
# Резервирование (StockReservation) — временная блокировка
# товара при добавлении в корзину. Живёт 15 минут,
# потом освобождается фоновым процессом.

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.stock import Stock
from app.models.inventory_move import InventoryMove, MoveType
from app.models.point import Point
from app.models.product import ProductVariant
from app.schemas import StockCreate, StockUpdate, StockAdjustment


async def get_stocks_by_point(
    db: AsyncSession,
    point_id: int,
    org_id: int,
) -> list[Stock]:
    """
    Получить все остатки на конкретной точке.

    Сначала проверяем что точка принадлежит организации.
    Возвращает список: какие варианты и сколько есть на точке.
    """
    # Проверяем что точка наша
    point_stmt = select(Point).where(
        Point.id == point_id,
        Point.org_id == org_id,
        Point.deleted_at.is_(None),
    )
    point_result = await db.execute(point_stmt)
    if not point_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Point not found")

    stmt = select(Stock).where(Stock.point_id == point_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_stocks_by_variant(
    db: AsyncSession,
    variant_id: int,
    org_id: int,
) -> list[Stock]:
    """
    Получить остатки варианта на всех точках.

    Полезно для админки: посмотреть на каких точках
    сколько лежит конкретного варианта товара.
    """
    # Проверяем что вариант принадлежит нашей организации
    # Идём через product → org_id
    variant_stmt = (
        select(ProductVariant)
        .join(ProductVariant.product)
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.product.has(org_id=org_id),
        )
    )
    variant_result = await db.execute(variant_stmt)
    if not variant_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Variant not found")

    stmt = select(Stock).where(Stock.product_variant_id == variant_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_stock(
    db: AsyncSession,
    org_id: int,
    data: StockCreate,
) -> Stock:
    """
    Создать запись остатка (привязать вариант к точке).

    Обычно вызывается при первой поставке товара на точку.
    Если запись уже существует — ошибка 409.
    """
    # Проверяем что точка наша
    point_stmt = select(Point).where(
        Point.id == data.point_id,
        Point.org_id == org_id,
    )
    if not (await db.execute(point_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Point not found")

    # Проверяем что такой записи ещё нет
    existing = await db.execute(
        select(Stock).where(
            Stock.product_variant_id == data.product_variant_id,
            Stock.point_id == data.point_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Stock record for this variant and point already exists",
        )

    stock = Stock(**data.model_dump())
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


async def adjust_stock(
    db: AsyncSession,
    stock_id: int,
    org_id: int,
    data: StockAdjustment,
    worker_id: int | None = None,
) -> Stock:
    """
    Корректировка остатка с записью в историю движений.

    delta > 0 — приход (поставка, возврат, корректировка вверх)
    delta < 0 — расход (списание, корректировка вниз)

    Каждая корректировка создаёт запись в inventory_moves,
    чтобы потом можно было отследить кто, когда и зачем менял остаток.
    """
    # Находим запись остатка
    stock = await db.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock record not found")

    # Проверяем принадлежность к организации через точку
    point_stmt = select(Point).where(
        Point.id == stock.point_id,
        Point.org_id == org_id,
    )
    if not (await db.execute(point_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Stock record not found")

    # Проверяем что после корректировки остаток не станет отрицательным
    new_quantity = stock.quantity + data.delta
    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Current: {stock.quantity}, adjustment: {data.delta}",
        )

    # Проверяем что остаток не упадёт ниже зарезервированного
    if new_quantity < stock.reserved_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reduce below reserved quantity ({stock.reserved_quantity})",
        )

    # Обновляем остаток
    stock.quantity = new_quantity

    # Записываем движение в историю
    move = InventoryMove(
        org_id=org_id,
        product_variant_id=stock.product_variant_id,
        # Приход — to_point, расход — from_point
        from_point_id=stock.point_id if data.delta < 0 else None,
        to_point_id=stock.point_id if data.delta > 0 else None,
        move_type=MoveType.ADJUSTMENT,
        quantity=abs(data.delta),
        notes=data.reason,
    )
    db.add(move)

    await db.commit()
    await db.refresh(stock)
    return stock


async def get_inventory_moves(
    db: AsyncSession,
    org_id: int,
    point_id: int | None = None,
    variant_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[InventoryMove]:
    """
    История движений товаров.

    Можно фильтровать по точке и/или варианту.
    Сортировка — от новых к старым.
    """
    stmt = (
        select(InventoryMove)
        .where(InventoryMove.org_id == org_id)
        .order_by(InventoryMove.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if point_id is not None:
        # Движение связано с точкой если она в from или to
        stmt = stmt.where(
            (InventoryMove.from_point_id == point_id)
            | (InventoryMove.to_point_id == point_id)
        )

    if variant_id is not None:
        stmt = stmt.where(InventoryMove.product_variant_id == variant_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_low_stock(
    db: AsyncSession,
    org_id: int,
) -> list[Stock]:
    """
    Получить список остатков ниже минимального порога.

    Возвращает записи где quantity <= min_quantity.
    Используется для уведомлений и отображения в админке.
    """
    stmt = (
        select(Stock)
        .join(Point, Stock.point_id == Point.id)
        .where(
            Point.org_id == org_id,
            Stock.quantity <= Stock.min_quantity,
            Stock.min_quantity > 0,  # пропускаем записи где порог не настроен
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())