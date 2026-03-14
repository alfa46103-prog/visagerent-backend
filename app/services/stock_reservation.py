# Файл: app/services/stock_reservation.py
# Назначение:
# Управление резервами товаров.
#
# Когда товар добавляется в корзину — создаётся резерв.
# Когда корзина очищается или заказ отменяется — резерв освобождается.
# Когда заказ подтверждается — резерв превращается в списание.

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.stock import Stock
from app.models.stock_reservation import StockReservation


RESERVATION_TTL_MINUTES = 15


async def reserve_stock(
    db: AsyncSession,
    variant_id: int,
    point_id: int,
    org_user_id: int,
    quantity: int,
):
    """
    Создать резерв товара.

    Проверяет что товара хватает и увеличивает reserved_quantity.
    """

    # блокируем строку склада
    stmt = (
        select(Stock)
        .where(
            Stock.product_variant_id == variant_id,
            Stock.point_id == point_id,
        )
        .with_for_update()
    )

    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    available = stock.quantity - stock.reserved_quantity

    if available < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Available: {available}",
        )

    # увеличиваем резерв
    stock.reserved_quantity += quantity

    reservation = StockReservation(
        product_variant_id=variant_id,
        point_id=point_id,
        org_user_id=org_user_id,
        quantity=quantity,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESERVATION_TTL_MINUTES),
    )

    db.add(reservation)

    await db.commit()
    await db.refresh(reservation)

    return reservation


async def release_reservation(
    db: AsyncSession,
    reservation_id: int,
):
    """
    Освобождает резерв (например при удалении из корзины).
    """

    reservation = await db.get(StockReservation, reservation_id)

    if not reservation or reservation.released_at:
        return

    stock_stmt = (
        select(Stock)
        .where(
            Stock.product_variant_id == reservation.product_variant_id,
            Stock.point_id == reservation.point_id,
        )
        .with_for_update()
    )

    result = await db.execute(stock_stmt)
    stock = result.scalar_one()

    stock.reserved_quantity -= reservation.quantity

    reservation.released_at = datetime.now(timezone.utc)

    await db.commit()

async def release_expired_reservations(db: AsyncSession):
    """
    Освобождает просроченные резервы.
    """

    now = datetime.now(timezone.utc)

    stmt = select(StockReservation).where(
        StockReservation.expires_at < now,
        StockReservation.released_at.is_(None),
    )

    result = await db.execute(stmt)
    reservations = result.scalars().all()

    count = 0

    for r in reservations:
        await release_reservation(db, r.id)
        count += 1

    return count