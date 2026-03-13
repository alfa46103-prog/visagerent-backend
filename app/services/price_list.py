# Файл: app/services/price_list.py
# Назначение: Сервис прайс-листов.
#
# Прайс-лист позволяет задать разные цены на варианты товаров.
# Если для варианта есть цена в активном прайс-листе — она используется
# вместо базовой цены варианта (product_variants.price).

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.price_list import PriceList
from app.models.price_list_item import PriceListItem


async def get_price_lists(db: AsyncSession, org_id: int) -> list[PriceList]:
    stmt = select(PriceList).where(PriceList.org_id == org_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_price_list(db: AsyncSession, org_id: int, data) -> PriceList:
    pl = PriceList(org_id=org_id, **data.model_dump())
    db.add(pl)
    await db.commit()
    await db.refresh(pl)
    return pl


async def delete_price_list(db: AsyncSession, pl_id: int, org_id: int) -> None:
    stmt = select(PriceList).where(PriceList.id == pl_id, PriceList.org_id == org_id)
    result = await db.execute(stmt)
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(status_code=404, detail="Price list not found")
    await db.delete(pl)
    await db.commit()


async def get_items(db: AsyncSession, pl_id: int) -> list[PriceListItem]:
    stmt = select(PriceListItem).where(PriceListItem.price_list_id == pl_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def set_item_price(db: AsyncSession, pl_id: int, data) -> PriceListItem:
    """Установить цену варианта в прайс-листе (upsert)."""
    stmt = select(PriceListItem).where(
        PriceListItem.price_list_id == pl_id,
        PriceListItem.product_variant_id == data.product_variant_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item:
        item.price = data.price
        if data.valid_from:
            item.valid_from = data.valid_from
        item.valid_until = data.valid_until
    else:
        item = PriceListItem(price_list_id=pl_id, **data.model_dump())
        db.add(item)

    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: int, pl_id: int) -> None:
    stmt = select(PriceListItem).where(
        PriceListItem.id == item_id,
        PriceListItem.price_list_id == pl_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Price list item not found")
    await db.delete(item)
    await db.commit()


async def get_effective_price(
    db: AsyncSession,
    variant_id: int,
    org_id: int,
    price_list_id: int | None = None,
) -> float | None:
    """
    Получить актуальную цену варианта из прайс-листа.

    Если price_list_id указан — ищем цену в этом прайс-листе.
    Если не указан — ищем в дефолтном прайс-листе.
    Если нет цены в прайс-листе — возвращаем None (используется базовая цена варианта).
    """
    now = datetime.now(timezone.utc)

    if price_list_id is None:
        # Ищем дефолтный прайс-лист
        pl_stmt = select(PriceList).where(
            PriceList.org_id == org_id,
            PriceList.is_default == True,
            PriceList.is_active == True,
        )
        pl_result = await db.execute(pl_stmt)
        pl = pl_result.scalar_one_or_none()
        if not pl:
            return None
        price_list_id = pl.id

    stmt = select(PriceListItem).where(
        PriceListItem.price_list_id == price_list_id,
        PriceListItem.product_variant_id == variant_id,
        PriceListItem.valid_from <= now,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        return None

    # Проверяем срок действия
    if item.valid_until and now > item.valid_until:
        return None

    return float(item.price)