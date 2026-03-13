# Файл: app/api/v1/endpoints/stock.py
# Назначение: HTTP-эндпоинты для складского учёта.
#
# Три группы:
#   /stock/point/{id}          — остатки на точке
#   /stock/variant/{id}        — остатки варианта по всем точкам
#   /stock/{id}/adjust         — корректировка остатка
#   /stock/moves               — история движений
#   /stock/low                 — товары с низким остатком

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import stock as stock_service
from app.schemas import (
    StockCreate, StockRead, StockAdjustment,
    InventoryMoveRead,
)

from app.tasks.stock_tasks import release_expired_reservations

router = APIRouter()


# ── Остатки ────────────────────────────────────────────

@router.get("/point/{point_id}", response_model=list[StockRead])
async def get_stocks_by_point(
    point_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """Все остатки на конкретной точке."""
    return await stock_service.get_stocks_by_point(db, point_id, current_worker.org_id)


@router.get("/variant/{variant_id}", response_model=list[StockRead])
async def get_stocks_by_variant(
    variant_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """Остатки варианта на всех точках."""
    return await stock_service.get_stocks_by_variant(db, variant_id, current_worker.org_id)


@router.get("/low", response_model=list[StockRead])
async def get_low_stock(
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """Товары с остатком ниже минимального порога."""
    return await stock_service.get_low_stock(db, current_worker.org_id)


@router.post("/", response_model=StockRead, status_code=201)
async def create_stock(
    data: StockCreate,
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """Создать запись остатка (привязать вариант к точке)."""
    return await stock_service.create_stock(db, current_worker.org_id, data)


# ── Корректировка ──────────────────────────────────────

@router.post("/{stock_id}/adjust", response_model=StockRead)
async def adjust_stock(
    stock_id: int,
    data: StockAdjustment,
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """
    Корректировка остатка.

    Примеры:
      {"delta": 50, "reason": "Поставка от поставщика"}
      {"delta": -3, "reason": "Списание — повреждённый товар"}
    """
    return await stock_service.adjust_stock(
        db, stock_id, current_worker.org_id, data, current_worker.id,
    )


# ── История движений ──────────────────────────────────

@router.get("/moves", response_model=list[InventoryMoveRead])
async def get_inventory_moves(
    point_id: int | None = Query(None, description="Фильтр по точке"),
    variant_id: int | None = Query(None, description="Фильтр по варианту"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """История движений товаров (поставки, продажи, списания и т.д.)."""
    return await stock_service.get_inventory_moves(
        db, current_worker.org_id,
        point_id=point_id,
        variant_id=variant_id,
        skip=skip,
        limit=limit,
    )





@router.post("/release-expired-reservations")
async def release_expired(
    current_worker: Worker = Depends(require_permission("can_manage_stock")),
    db: AsyncSession = Depends(get_db),
):
    """
    Освободить просроченные резервы вручную.
    В продакшне вызывается автоматически через Celery beat каждые 5 минут.
    """
    count = await release_expired_reservations(db)
    return {"released": count}