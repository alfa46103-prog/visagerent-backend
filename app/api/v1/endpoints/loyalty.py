# Файл: app/api/v1/endpoints/loyalty.py
# Назначение: HTTP-эндпоинты для лояльности, акций и рефералов.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import loyalty as loyalty_service
from app.services import promotion as promo_service
from app.schemas import (
    LoyaltyProgramCreate, LoyaltyProgramRead, LoyaltyProgramUpdate,
    LoyaltyTierCreate, LoyaltyTierRead, LoyaltyTierUpdate,
    LoyaltyTransactionRead, ManualPointsAdjustment,
    PromotionCreate, PromotionRead, PromotionUpdate,
)

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ПРОГРАММА ЛОЯЛЬНОСТИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/program", response_model=LoyaltyProgramRead | None)
async def get_program(
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Получить настройки программы лояльности."""
    return await loyalty_service.get_program(db, current_worker.org_id)


@router.post("/program", response_model=LoyaltyProgramRead, status_code=201)
async def create_program(
    data: LoyaltyProgramCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Создать программу лояльности."""
    return await loyalty_service.create_program(db, current_worker.org_id, data)


@router.patch("/program/{program_id}", response_model=LoyaltyProgramRead)
async def update_program(
    program_id: int,
    data: LoyaltyProgramUpdate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить настройки программы."""
    return await loyalty_service.update_program(db, program_id, current_worker.org_id, data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  УРОВНИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/tiers", response_model=list[LoyaltyTierRead])
async def get_tiers(
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Список уровней лояльности."""
    return await loyalty_service.get_tiers(db, current_worker.org_id)


@router.post("/tiers", response_model=LoyaltyTierRead, status_code=201)
async def create_tier(
    data: LoyaltyTierCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Создать уровень."""
    return await loyalty_service.create_tier(db, current_worker.org_id, data)


@router.patch("/tiers/{tier_id}", response_model=LoyaltyTierRead)
async def update_tier(
    tier_id: int,
    data: LoyaltyTierUpdate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить уровень."""
    return await loyalty_service.update_tier(db, tier_id, current_worker.org_id, data)


@router.delete("/tiers/{tier_id}", status_code=204)
async def delete_tier(
    tier_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить уровень."""
    await loyalty_service.delete_tier(db, tier_id, current_worker.org_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  БАЛЛЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/balance/{org_user_id}")
async def get_user_balance(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_clients")),
    db: AsyncSession = Depends(get_db),
):
    """Баланс баллов покупателя."""
    balance = await loyalty_service.get_user_balance(db, org_user_id, current_worker.org_id)
    return {"org_user_id": org_user_id, "balance": balance}


@router.get("/transactions/{org_user_id}", response_model=list[LoyaltyTransactionRead])
async def get_user_transactions(
    org_user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("can_view_clients")),
    db: AsyncSession = Depends(get_db),
):
    """История транзакций баллов покупателя."""
    return await loyalty_service.get_user_transactions(
        db, org_user_id, current_worker.org_id, skip, limit,
    )


@router.post("/adjust", response_model=LoyaltyTransactionRead)
async def manual_adjust_points(
    data: ManualPointsAdjustment,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Ручное начисление/списание баллов."""
    return await loyalty_service.manual_adjust_points(db, current_worker.org_id, data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  АКЦИИ И ПРОМОКОДЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/promotions", response_model=list[PromotionRead])
async def get_promotions(
    is_active: bool | None = Query(None),
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Список акций."""
    return await promo_service.get_promotions(db, current_worker.org_id, is_active)


@router.post("/promotions", response_model=PromotionRead, status_code=201)
async def create_promotion(
    data: PromotionCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Создать акцию."""
    return await promo_service.create_promotion(db, current_worker.org_id, data)


@router.patch("/promotions/{promotion_id}", response_model=PromotionRead)
async def update_promotion(
    promotion_id: int,
    data: PromotionUpdate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить акцию."""
    return await promo_service.update_promotion(db, promotion_id, current_worker.org_id, data)


@router.delete("/promotions/{promotion_id}", status_code=204)
async def delete_promotion(
    promotion_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить акцию."""
    await promo_service.delete_promotion(db, promotion_id, current_worker.org_id)