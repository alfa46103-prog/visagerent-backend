# Файл: app/services/cart.py
# Назначение: Сервис корзины покупателя.
#
# Корзина привязана к OrganizationUser (покупатель в конкретной организации)
# и к Point (выбранная точка продаж).
#
# При добавлении товара в корзину:
#   1. Проверяем что вариант существует и активен
#   2. Проверяем остаток на выбранной точке
#   3. Фиксируем текущую цену (price_snapshot)
#   4. Создаём резерв (stock_reservation) на 15 минут
#
# При оформлении заказа корзина конвертируется в Order + OrderItems,
# а записи CartItem удаляются.

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.cart_item import CartItem
from app.models.product import ProductVariant, Product
from app.models.stock import Stock
from app.models.stock_reservation import StockReservation
from app.models.user_point_session import UserPointSession
from app.schemas import CartItemAdd, CartItemUpdate

# Время жизни резерва в минутах
RESERVATION_TTL_MINUTES = 15


async def _get_user_point_id(
    db: AsyncSession,
    org_user_id: int,
) -> int:
    """
    Получить ID текущей точки пользователя.

    Покупатель при первом входе в каталог выбирает точку,
    она сохраняется в user_point_sessions.
    Все операции с корзиной привязаны к этой точке.
    """
    stmt = select(UserPointSession).where(
        UserPointSession.org_user_id == org_user_id
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=400,
            detail="No point selected. Please choose a pickup point first.",
        )
    return session.point_id


async def _check_available_stock(
    db: AsyncSession,
    variant_id: int,
    point_id: int,
    required_quantity: int,
) -> Stock:
    """
    Проверить что на точке достаточно товара.

    Доступное количество = quantity - reserved_quantity.
    Если не хватает — ошибка 400.
    """
    stmt = select(Stock).where(
        Stock.product_variant_id == variant_id,
        Stock.point_id == point_id,
    )
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=400, detail="Product not available at this point")

    available = stock.quantity - stock.reserved_quantity
    if available < required_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Available: {available}",
        )

    return stock


async def get_cart(
    db: AsyncSession,
    org_user_id: int,
) -> list[CartItem]:
    """
    Получить содержимое корзины покупателя.

    Возвращает все CartItem для данного пользователя.
    """
    stmt = select(CartItem).where(CartItem.org_user_id == org_user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_to_cart(
    db: AsyncSession,
    org_user_id: int,
    data: CartItemAdd,
) -> CartItem:
    """
    Добавить товар в корзину.

    Логика:
      1. Определяем текущую точку пользователя
      2. Проверяем что вариант существует и активен
      3. Получаем текущую цену варианта
      4. Проверяем остаток на точке
      5. Если товар уже в корзине — увеличиваем количество
      6. Если нет — создаём новую запись
      7. Создаём резерв (reserved_quantity в stock)
    """
    # 1. Получаем точку пользователя
    point_id = await _get_user_point_id(db, org_user_id)

    # 2. Проверяем вариант
    variant = await db.get(ProductVariant, data.product_variant_id)
    if not variant or not variant.is_active or variant.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Product variant not found or inactive")

    # 3. Текущая цена
    current_price = float(variant.price)

    # 4. Проверяем остаток
    stock = await _check_available_stock(db, variant.id, point_id, data.quantity)

    # 5. Проверяем — может товар уже в корзине?
    existing_stmt = select(CartItem).where(
        CartItem.org_user_id == org_user_id,
        CartItem.product_variant_id == variant.id,
        CartItem.point_id == point_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing_item = existing_result.scalar_one_or_none()

    if existing_item:
        # Товар уже в корзине — увеличиваем количество
        new_quantity = existing_item.quantity + data.quantity

        # Перепроверяем остаток для нового количества
        await _check_available_stock(db, variant.id, point_id, new_quantity)

        existing_item.quantity = new_quantity
        existing_item.price_snapshot = current_price
        cart_item = existing_item
    else:
        # 6. Создаём новую запись в корзине
        cart_item = CartItem(
            org_user_id=org_user_id,
            product_variant_id=variant.id,
            point_id=point_id,
            quantity=data.quantity,
            price_snapshot=current_price,
        )
        db.add(cart_item)

    # 7. Увеличиваем резерв на складе
    stock.reserved_quantity += data.quantity

    # Создаём запись резервации (для фонового процесса освобождения)
    reservation = StockReservation(
        product_variant_id=variant.id,
        point_id=point_id,
        org_user_id=org_user_id,
        quantity=data.quantity,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESERVATION_TTL_MINUTES),
    )
    db.add(reservation)

    await db.commit()
    await db.refresh(cart_item)
    return cart_item


async def update_cart_item(
    db: AsyncSession,
    cart_item_id: int,
    org_user_id: int,
    data: CartItemUpdate,
) -> CartItem:
    """
    Изменить количество товара в корзине.

    Если новое количество больше текущего — проверяем остаток
    и добавляем резерв на разницу.
    Если меньше — освобождаем часть резерва.
    """
    # Находим элемент корзины
    stmt = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.org_user_id == org_user_id,
    )
    result = await db.execute(stmt)
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    # Разница между новым и старым количеством
    delta = data.quantity - cart_item.quantity

    if delta > 0:
        # Нужно больше — проверяем остаток
        stock = await _check_available_stock(
            db, cart_item.product_variant_id, cart_item.point_id, delta,
        )
        stock.reserved_quantity += delta
    elif delta < 0:
        # Нужно меньше — освобождаем резерв
        stock_stmt = select(Stock).where(
            Stock.product_variant_id == cart_item.product_variant_id,
            Stock.point_id == cart_item.point_id,
        )
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        if stock:
            stock.reserved_quantity = max(0, stock.reserved_quantity + delta)

    cart_item.quantity = data.quantity

    await db.commit()
    await db.refresh(cart_item)
    return cart_item


async def remove_from_cart(
    db: AsyncSession,
    cart_item_id: int,
    org_user_id: int,
) -> None:
    """
    Удалить товар из корзины.

    Освобождает резерв на складе.
    """
    stmt = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.org_user_id == org_user_id,
    )
    result = await db.execute(stmt)
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Освобождаем резерв
    stock_stmt = select(Stock).where(
        Stock.product_variant_id == cart_item.product_variant_id,
        Stock.point_id == cart_item.point_id,
    )
    stock_result = await db.execute(stock_stmt)
    stock = stock_result.scalar_one_or_none()
    if stock:
        stock.reserved_quantity = max(0, stock.reserved_quantity - cart_item.quantity)

    # Удаляем из корзины
    await db.delete(cart_item)
    await db.commit()


async def clear_cart(
    db: AsyncSession,
    org_user_id: int,
) -> None:
    """
    Очистить всю корзину пользователя.

    Освобождает все резервы. Вызывается:
      - когда покупатель нажимает "Очистить корзину"
      - после успешного оформления заказа
    """
    # Получаем все элементы корзины
    items = await get_cart(db, org_user_id)

    # Освобождаем резервы для каждого элемента
    for item in items:
        stock_stmt = select(Stock).where(
            Stock.product_variant_id == item.product_variant_id,
            Stock.point_id == item.point_id,
        )
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        if stock:
            stock.reserved_quantity = max(0, stock.reserved_quantity - item.quantity)

    # Удаляем все записи корзины одним запросом
    await db.execute(
        delete(CartItem).where(CartItem.org_user_id == org_user_id)
    )
    await db.commit()



async def validate_cart_prices(
    db: AsyncSession,
    org_user_id: int,
) -> list[dict]:
    """
    Проверить актуальность цен в корзине.

    Сравниваем price_snapshot (цена на момент добавления)
    с текущей ценой варианта. Если цена изменилась —
    возвращаем список расхождений.

    Вызывается перед оформлением заказа.

    Возвращает:
        [] — всё актуально
        [{"cart_item_id": 1, "old_price": 500, "new_price": 600, "variant_id": 10}, ...]
    """
    items = await get_cart(db, org_user_id)
    mismatches = []

    for item in items:
        variant = await db.get(ProductVariant, item.product_variant_id)
        if not variant:
            continue

        current_price = float(variant.price)
        snapshot_price = float(item.price_snapshot) if item.price_snapshot else 0

        if abs(current_price - snapshot_price) > 0.01:  # допуск на копейки
            mismatches.append({
                "cart_item_id": item.id,
                "variant_id": variant.id,
                "old_price": snapshot_price,
                "new_price": current_price,
            })

    return mismatches


async def refresh_cart_prices(
    db: AsyncSession,
    org_user_id: int,
) -> list[CartItem]:
    """
    Обновить цены в корзине до актуальных.
    Вызывается покупателем если он согласен с новыми ценами.
    """
    items = await get_cart(db, org_user_id)

    for item in items:
        variant = await db.get(ProductVariant, item.product_variant_id)
        if variant:
            item.price_snapshot = float(variant.price)

    await db.commit()
    return await get_cart(db, org_user_id)