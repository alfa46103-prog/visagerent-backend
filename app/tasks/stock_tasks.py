# Файл: app/tasks/stock_tasks.py
# Назначение: Фоновые задачи для склада.
#
# release_expired_reservations — освобождает просроченные резервы.
# Запускается периодически (каждые 5 минут) через Celery beat
# или вручную через вызов функции.
#
# Пока без Celery — функция async, можно вызывать напрямую
# или через FastAPI background task. Когда подключишь Celery —
# просто обернёшь в @celery_app.task.

from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_reservation import StockReservation
from app.models.stock import Stock


async def release_expired_reservations(db: AsyncSession) -> int:
    """
    Освободить просроченные резервы.

    Логика:
      1. Находим все резервы где expires_at < сейчас и released_at IS NULL и order_id IS NULL
         (order_id IS NULL означает что резерв ещё не конвертирован в заказ)
      2. Для каждого — уменьшаем reserved_quantity в stock
      3. Помечаем резерв как released (released_at = now)

    Возвращает количество освобождённых резервов.
    """
    now = datetime.now(timezone.utc)

    # Находим просроченные резервы которые ещё не освобождены и не привязаны к заказу
    stmt = select(StockReservation).where(
        StockReservation.expires_at < now,
        StockReservation.released_at.is_(None),
        StockReservation.order_id.is_(None),
    )
    result = await db.execute(stmt)
    expired_reservations = list(result.scalars().all())

    released_count = 0

    for reservation in expired_reservations:
        # Уменьшаем reserved_quantity на складе
        stock_stmt = select(Stock).where(
            Stock.product_variant_id == reservation.product_variant_id,
            Stock.point_id == reservation.point_id,
        )
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()

        if stock:
            stock.reserved_quantity = max(0, stock.reserved_quantity - reservation.quantity)

        # Помечаем резерв как освобождённый
        reservation.released_at = now
        released_count += 1

    if released_count > 0:
        await db.commit()

    return released_count