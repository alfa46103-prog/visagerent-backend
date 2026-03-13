# Файл: app/services/promotion.py
# Назначение: Сервис акций и промокодов.
#
# Акция может быть:
#   - автоматической (применяется при выполнении условий)
#   - по промокоду (покупатель вводит код)
#
# Типы скидок:
#   percent — процент от суммы
#   fixed_rub — фиксированная сумма
#   free_shipping — бесплатная доставка
#   gift_product — подарок при покупке

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.promotion import Promotion
from app.models.promotion_use import PromotionUse
from app.schemas import PromotionCreate, PromotionUpdate


async def get_promotions(
    db: AsyncSession,
    org_id: int,
    is_active: bool | None = None,
) -> list[Promotion]:
    """Список акций организации."""
    stmt = select(Promotion).where(Promotion.org_id == org_id)

    if is_active is not None:
        stmt = stmt.where(Promotion.is_active == is_active)

    stmt = stmt.order_by(Promotion.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_promotion_by_id(
    db: AsyncSession,
    promotion_id: int,
    org_id: int,
) -> Promotion:
    """Получить акцию по ID."""
    stmt = select(Promotion).where(
        Promotion.id == promotion_id,
        Promotion.org_id == org_id,
    )
    result = await db.execute(stmt)
    promo = result.scalar_one_or_none()

    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promo


async def create_promotion(
    db: AsyncSession,
    org_id: int,
    data: PromotionCreate,
) -> Promotion:
    """Создать акцию."""
    # Если указан промокод — проверяем уникальность
    if data.promo_code:
        existing = await db.execute(
            select(Promotion).where(Promotion.promo_code == data.promo_code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Promo code already exists")

    promo = Promotion(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


async def update_promotion(
    db: AsyncSession,
    promotion_id: int,
    org_id: int,
    data: PromotionUpdate,
) -> Promotion:
    """Обновить акцию."""
    promo = await get_promotion_by_id(db, promotion_id, org_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promo, field, value)

    await db.commit()
    await db.refresh(promo)
    return promo


async def delete_promotion(
    db: AsyncSession,
    promotion_id: int,
    org_id: int,
) -> None:
    """Удалить акцию."""
    promo = await get_promotion_by_id(db, promotion_id, org_id)
    await db.delete(promo)
    await db.commit()


async def validate_promo_code(
    db: AsyncSession,
    org_id: int,
    promo_code: str,
    org_user_id: int,
    order_total: float,
) -> Promotion:
    """
    Проверить промокод и вернуть акцию если он валидный.

    Проверки:
      1. Промокод существует и принадлежит организации
      2. Акция активна
      3. Текущая дата в пределах starts_at — ends_at
      4. Не превышен общий лимит использований (max_uses)
      5. Не превышен лимит для этого покупателя (per_user_limit)
      6. Сумма заказа >= min_order
    """
    # 1. Ищем промокод
    stmt = select(Promotion).where(
        Promotion.promo_code == promo_code,
        Promotion.org_id == org_id,
    )
    result = await db.execute(stmt)
    promo = result.scalar_one_or_none()

    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    # 2. Активна?
    if not promo.is_active:
        raise HTTPException(status_code=400, detail="Promotion is not active")

    # 3. Период действия
    now = datetime.now(timezone.utc)
    if promo.starts_at and now < promo.starts_at:
        raise HTTPException(status_code=400, detail="Promotion has not started yet")
    if promo.ends_at and now > promo.ends_at:
        raise HTTPException(status_code=400, detail="Promotion has expired")

    # 4. Общий лимит
    if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Promotion usage limit reached")

    # 5. Лимит на покупателя
    user_uses_stmt = select(PromotionUse).where(
        PromotionUse.promotion_id == promo.id,
        PromotionUse.org_user_id == org_user_id,
    )
    user_uses_result = await db.execute(user_uses_stmt)
    user_uses_count = len(list(user_uses_result.scalars().all()))

    if user_uses_count >= promo.per_user_limit:
        raise HTTPException(status_code=400, detail="You have already used this promo code")

    # 6. Минимальная сумма
    if order_total < float(promo.min_order):
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order amount: {promo.min_order}",
        )

    return promo


async def record_promotion_use(
    db: AsyncSession,
    promotion_id: int,
    org_user_id: int,
    order_id: int,
    discount_applied: float,
) -> None:
    """
    Зафиксировать использование акции.
    Вызывается после оформления заказа с промокодом.
    """
    use = PromotionUse(
        promotion_id=promotion_id,
        org_user_id=org_user_id,
        order_id=order_id,
        discount_applied=discount_applied,
    )
    db.add(use)

    # Увеличиваем счётчик использований
    promo = await db.get(Promotion, promotion_id)
    if promo:
        promo.uses_count += 1

    await db.commit()