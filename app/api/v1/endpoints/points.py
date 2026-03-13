# Файл: app/api/v1/endpoints/points.py
# Назначение: HTTP-эндпоинты для точек продаж.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import point as point_service
from app.schemas import PointCreate, PointRead, PointUpdate

router = APIRouter()


@router.get("/", response_model=list[PointRead])
async def get_points(
    is_active: bool | None = Query(None),
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Список точек продаж организации."""
    return await point_service.get_points(db, current_worker.org_id, is_active)


@router.get("/{point_id}", response_model=PointRead)
async def get_point(
    point_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Получить точку по ID."""
    return await point_service.get_point_by_id(db, point_id, current_worker.org_id)


@router.post("/", response_model=PointRead, status_code=201)
async def create_point(
    data: PointCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Создать точку продаж."""
    return await point_service.create_point(db, current_worker.org_id, data)


@router.patch("/{point_id}", response_model=PointRead)
async def update_point(
    point_id: int,
    data: PointUpdate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить точку."""
    return await point_service.update_point(db, point_id, current_worker.org_id, data)


@router.delete("/{point_id}", status_code=204)
async def delete_point(
    point_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Мягкое удаление точки."""
    await point_service.delete_point(db, point_id, current_worker.org_id)