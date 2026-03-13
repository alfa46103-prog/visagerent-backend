# Файл: app/services/loyalty.py
# Назначение: Сервис программы лояльности.
#
# Три основные части:
#   1. Программа (LoyaltyProgram) — настройки начисления баллов
#   2. Уровни (LoyaltyTier) — бронза/серебро/золото
#   3. Транзакции (LoyaltyTransaction) — история начислений/списаний
#
# Баллы начисляются при выполнении заказа (статус COMPLETED).
# Уровень покупателя определяется по total_orders_amount в OrganizationUser.

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.loyalty_program import LoyaltyProgram
from app.models.loyalty_tier import LoyaltyTier
from app.models.loyalty_transaction import LoyaltyTransaction, LoyaltyTxType
from app.models.organization_user import OrganizationUser
from app.schemas import (
    LoyaltyProgramCreate, LoyaltyProgramUpdate,
    LoyaltyTierCreate, LoyaltyTierUpdate,
    ManualPointsAdjustment,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ПРОГРАММА ЛОЯЛЬНОСТИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_program(
    db: AsyncSession,
    org_id: int,
) -> LoyaltyProgram | None:
    """
    Получить программу лояльности организации.
    У организации может быть одна активная программа.
    """
    stmt = select(LoyaltyProgram).where(
        LoyaltyProgram.org_id == org_id,
        LoyaltyProgram.is_active == True,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_program(
    db: AsyncSession,
    org_id: int,
    data: LoyaltyProgramCreate,
) -> LoyaltyProgram:
    """Создать программу лояльности."""
    program = LoyaltyProgram(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


async def update_program(
    db: AsyncSession,
    program_id: int,
    org_id: int,
    data: LoyaltyProgramUpdate,
) -> LoyaltyProgram:
    """Обновить настройки программы."""
    stmt = select(LoyaltyProgram).where(
        LoyaltyProgram.id == program_id,
        LoyaltyProgram.org_id == org_id,
    )
    result = await db.execute(stmt)
    program = result.scalar_one_or_none()

    if not program:
        raise HTTPException(status_code=404, detail="Loyalty program not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(program, field, value)

    await db.commit()
    await db.refresh(program)
    return program


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  УРОВНИ ЛОЯЛЬНОСТИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_tiers(
    db: AsyncSession,
    org_id: int,
) -> list[LoyaltyTier]:
    """Получить все уровни организации, отсортированные по приоритету."""
    stmt = (
        select(LoyaltyTier)
        .where(LoyaltyTier.org_id == org_id)
        .order_by(LoyaltyTier.priority)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_tier(
    db: AsyncSession,
    org_id: int,
    data: LoyaltyTierCreate,
) -> LoyaltyTier:
    """Создать уровень лояльности."""
    tier = LoyaltyTier(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return tier


async def update_tier(
    db: AsyncSession,
    tier_id: int,
    org_id: int,
    data: LoyaltyTierUpdate,
) -> LoyaltyTier:
    """Обновить уровень."""
    stmt = select(LoyaltyTier).where(
        LoyaltyTier.id == tier_id,
        LoyaltyTier.org_id == org_id,
    )
    result = await db.execute(stmt)
    tier = result.scalar_one_or_none()

    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tier, field, value)

    await db.commit()
    await db.refresh(tier)
    return tier


async def delete_tier(
    db: AsyncSession,
    tier_id: int,
    org_id: int,
) -> None:
    """Удалить уровень."""
    stmt = select(LoyaltyTier).where(
        LoyaltyTier.id == tier_id,
        LoyaltyTier.org_id == org_id,
    )
    result = await db.execute(stmt)
    tier = result.scalar_one_or_none()

    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    await db.delete(tier)
    await db.commit()


async def recalculate_user_tier(
    db: AsyncSession,
    org_user_id: int,
    org_id: int,
) -> None:
    """
    Пересчитать уровень покупателя.

    Берём total_orders_amount из OrganizationUser
    и находим максимальный уровень, порог которого
    пользователь уже достиг.

    Вызывается:
      - после выполнения заказа (COMPLETED)
      - вручную администратором
    """
    # Получаем пользователя
    user = await db.get(OrganizationUser, org_user_id)
    if not user or user.org_id != org_id:
        return

    # Получаем все уровни организации, отсортированные по порогу (от большего к меньшему)
    stmt = (
        select(LoyaltyTier)
        .where(LoyaltyTier.org_id == org_id)
        .order_by(LoyaltyTier.min_orders_amount.desc())
    )
    result = await db.execute(stmt)
    tiers = list(result.scalars().all())

    # Находим подходящий уровень
    new_tier_id = None
    for tier in tiers:
        if float(user.total_orders_amount) >= float(tier.min_orders_amount):
            new_tier_id = tier.id
            break  # берём первый подходящий (самый высокий)

    # Обновляем уровень пользователя
    user.tier_id = new_tier_id
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ТРАНЗАКЦИИ БАЛЛОВ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_user_balance(
    db: AsyncSession,
    org_user_id: int,
    org_id: int,
) -> float:
    """
    Получить текущий баланс баллов покупателя.
    Сумма available_points по всем неистёкшим транзакциям.
    """
    stmt = select(func.coalesce(func.sum(LoyaltyTransaction.available_points), 0)).where(
        LoyaltyTransaction.org_user_id == org_user_id,
        LoyaltyTransaction.org_id == org_id,
        LoyaltyTransaction.is_expired == False,
    )
    result = await db.execute(stmt)
    return float(result.scalar())


async def get_user_transactions(
    db: AsyncSession,
    org_user_id: int,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[LoyaltyTransaction]:
    """Получить историю транзакций баллов покупателя."""
    stmt = (
        select(LoyaltyTransaction)
        .where(
            LoyaltyTransaction.org_user_id == org_user_id,
            LoyaltyTransaction.org_id == org_id,
        )
        .order_by(LoyaltyTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def accrue_points_for_order(
    db: AsyncSession,
    org_id: int,
    org_user_id: int,
    order_id: int,
    order_total: float,
) -> LoyaltyTransaction | None:
    """
    Начислить баллы за выполненный заказ.

    Вызывается когда заказ переходит в статус COMPLETED.

    Логика:
      1. Находим активную программу лояльности
      2. Проверяем что сумма заказа >= min_order_for_accrual
      3. Считаем баллы: order_total * accrual_percent / 100
      4. Учитываем множитель уровня покупателя
      5. Создаём транзакцию
    """
    # Находим программу
    program = await get_program(db, org_id)
    if not program:
        return None  # лояльность не настроена

    # Проверяем минимальную сумму
    if order_total < float(program.min_order_for_accrual):
        return None

    # Базовое начисление
    points = order_total * float(program.accrual_percent) / 100

    # Учитываем множитель уровня покупателя
    user = await db.get(OrganizationUser, org_user_id)
    if user and user.tier_id:
        tier = await db.get(LoyaltyTier, user.tier_id)
        if tier:
            points *= float(tier.accrual_multiplier)

    # Округляем до 2 знаков
    points = round(points, 2)

    if points <= 0:
        return None

    # Срок действия баллов
    expires_at = None
    if program.points_expire_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=program.points_expire_days)

    # Создаём транзакцию
    tx = LoyaltyTransaction(
        org_id=org_id,
        program_id=program.id,
        org_user_id=org_user_id,
        order_id=order_id,
        points=points,
        available_points=points,
        type=LoyaltyTxType.ORDER_ACCRUAL,
        description=f"Начисление за заказ",
        expires_at=expires_at,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def manual_adjust_points(
    db: AsyncSession,
    org_id: int,
    data: ManualPointsAdjustment,
) -> LoyaltyTransaction:
    """
    Ручное начисление/списание баллов администратором.

    Используется когда нужно:
      - начислить бонус за отзыв
      - компенсировать проблему с заказом
      - списать баллы по просьбе покупателя
    """
    # Проверяем что пользователь из нашей организации
    user = await db.get(OrganizationUser, data.org_user_id)
    if not user or user.org_id != org_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Находим программу
    program = await get_program(db, org_id)
    if not program:
        raise HTTPException(status_code=400, detail="Loyalty program not configured")

    # При списании проверяем баланс
    if data.points < 0:
        balance = await get_user_balance(db, data.org_user_id, org_id)
        if balance + data.points < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Current: {balance}",
            )

    tx = LoyaltyTransaction(
        org_id=org_id,
        program_id=program.id,
        org_user_id=data.org_user_id,
        points=data.points,
        available_points=max(0, data.points),  # при списании available = 0
        type=LoyaltyTxType.MANUAL_ADJUSTMENT,
        description=data.description or "Ручная корректировка",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def revoke_points_for_order(
    db: AsyncSession,
    org_id: int,
    org_user_id: int,
    order_id: int,
) -> LoyaltyTransaction | None:
    """
    Отозвать баллы, начисленные за конкретный заказ.

    Вызывается при отмене или возврате заказа.

    Логика:
      1. Ищем транзакцию начисления за этот заказ
      2. Если нашли — создаём обратную транзакцию (отрицательные баллы)
      3. Обнуляем available_points у исходной транзакции

    Если баллы уже были потрачены (available_points < points),
    всё равно создаём обратную транзакцию на полную сумму —
    баланс может уйти в минус, администратор разберётся.
    """
    # Ищем исходное начисление за этот заказ
    stmt = select(LoyaltyTransaction).where(
        LoyaltyTransaction.order_id == order_id,
        LoyaltyTransaction.org_user_id == org_user_id,
        LoyaltyTransaction.type == LoyaltyTxType.ORDER_ACCRUAL,
    )
    result = await db.execute(stmt)
    original_tx = result.scalar_one_or_none()

    if not original_tx:
        return None  # баллы за этот заказ не начислялись

    # Сколько баллов было начислено
    points_to_revoke = float(original_tx.points)

    # Обнуляем доступные баллы у исходной транзакции
    original_tx.available_points = 0

    # Находим программу для создания транзакции
    program = await get_program(db, org_id)
    if not program:
        return None

    # Создаём обратную транзакцию (отрицательные баллы)
    revoke_tx = LoyaltyTransaction(
        org_id=org_id,
        program_id=program.id,
        org_user_id=org_user_id,
        order_id=order_id,
        points=-points_to_revoke,          # отрицательное значение
        available_points=0,                 # у списания нет доступных баллов
        type=LoyaltyTxType.REFUND,
        description="Возврат баллов — заказ отменён/возвращён",
    )
    db.add(revoke_tx)

    await db.commit()
    await db.refresh(revoke_tx)
    return revoke_tx


async def process_referral_bonus(
    db: AsyncSession,
    org_id: int,
    org_user_id: int,
    order_id: int,
) -> None:
    """
    Начислить реферальный бонус при первом выполненном заказе приглашённого.

    Вызывается из change_order_status при COMPLETED.

    Логика:
      1. Проверяем что у покупателя есть referrer_id (кто пригласил)
      2. Проверяем что это первый выполненный заказ (раньше бонус не начислялся)
      3. Находим реферальный код реферера
      4. Начисляем баллы рефереру (bonus_points) и новому пользователю (new_user_bonus)
    """
    from app.models.referral_code import ReferralCode

    # Получаем покупателя
    user = await db.get(OrganizationUser, org_user_id)
    if not user or not user.referrer_id:
        return  # нет реферера — ничего не делаем

    # Проверяем что реферальный бонус ещё не начислялся
    existing_stmt = select(LoyaltyTransaction).where(
        LoyaltyTransaction.org_user_id == org_user_id,
        LoyaltyTransaction.type == LoyaltyTxType.REFERRAL_BONUS,
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        return  # бонус уже начислен

    # Находим программу лояльности
    program = await get_program(db, org_id)
    if not program:
        return

    # Находим реферальный код реферера
    referral_stmt = select(ReferralCode).where(
        ReferralCode.org_user_id == user.referrer_id,
        ReferralCode.is_active == True,
    )
    referral_result = await db.execute(referral_stmt)
    referral_code = referral_result.scalar_one_or_none()

    if not referral_code:
        return

    # Начисляем бонус рефереру
    if float(referral_code.bonus_points) > 0:
        tx_referrer = LoyaltyTransaction(
            org_id=org_id,
            program_id=program.id,
            org_user_id=user.referrer_id,
            points=float(referral_code.bonus_points),
            available_points=float(referral_code.bonus_points),
            type=LoyaltyTxType.REFERRAL_BONUS,
            description="Реферальный бонус — приглашённый сделал первый заказ",
        )
        db.add(tx_referrer)

    # Начисляем бонус новому пользователю
    if float(referral_code.new_user_bonus) > 0:
        tx_new_user = LoyaltyTransaction(
            org_id=org_id,
            program_id=program.id,
            org_user_id=org_user_id,
            points=float(referral_code.new_user_bonus),
            available_points=float(referral_code.new_user_bonus),
            type=LoyaltyTxType.REFERRAL_BONUS,
            description="Бонус за первый заказ по реферальной ссылке",
        )
        db.add(tx_new_user)

    # Увеличиваем счётчик использований кода
    referral_code.uses_count += 1

    await db.commit()