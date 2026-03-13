# Файл: app/api/v1/endpoints/orders.py
# Назначение: HTTP-эндпоинты для управления заказами.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import order as order_service
from app.schemas import (
    OrderCreate, OrderRead, OrderStatusChange, OrderStatusHistoryRead,
)

router = APIRouter()


@router.get("/", response_model=list[OrderRead])
async def get_orders(
    status: str | None = Query(None, description="Фильтр по статусу"),
    point_id: int | None = Query(None, description="Фильтр по точке"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Список заказов с фильтрацией."""
    return await order_service.get_orders(
        db, current_worker.org_id,
        status=status,
        point_id=point_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Получить заказ по ID."""
    return await order_service.get_order_by_id(db, order_id, current_worker.org_id)


@router.post("/", response_model=OrderRead, status_code=201)
async def create_order(
    org_user_id: int,
    data: OrderCreate,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать заказ из корзины покупателя.

    В будущем этот эндпоинт будет вызываться из Telegram-бота,
    а org_user_id будет браться из токена покупателя.
    """
    return await order_service.create_order_from_cart(
        db, org_user_id, current_worker.org_id, data,
    )


@router.post("/{order_id}/status", response_model=OrderRead)
async def change_order_status(
    order_id: int,
    data: OrderStatusChange,
    current_worker: Worker = Depends(require_permission("can_confirm_orders")),
    db: AsyncSession = Depends(get_db),
):
    """
    Сменить статус заказа.

    Допустимые переходы:
      pending → confirmed, cancelled
      confirmed → processing, cancelled
      processing → ready, cancelled
      ready → completed, cancelled
      completed → refunded
    """
    return await order_service.change_order_status(
        db, order_id, current_worker.org_id, data, current_worker.id,
    )


@router.get("/{order_id}/history", response_model=list[OrderStatusHistoryRead])
async def get_order_history(
    order_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """История статусов заказа."""
    return await order_service.get_order_history(
        db, order_id, current_worker.org_id,
    )