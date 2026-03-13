# Файл: app/api/v1/endpoints/categories.py
# Назначение: HTTP-эндпоинты для управления категориями товаров.
#
# Два уровня доступа:
#   - Чтение (get, tree): can_view_products
#   - Изменение (create, update, delete): can_edit_products

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import category as category_service
from app.schemas import (
    CategoryCreate, CategoryRead, CategoryUpdate, CategoryTreeRead,
)

router = APIRouter()


@router.get("/", response_model=list[CategoryRead])
async def get_categories(
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Список категорий организации (плоский)."""
    return await category_service.get_categories(
        db, current_worker.org_id, is_active=is_active,
    )


@router.get("/tree", response_model=list[CategoryTreeRead])
async def get_category_tree(
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """
    Дерево категорий (вложенная структура).
    Используется для навигации в боте и сайдбара в админке.
    """
    return await category_service.get_category_tree(db, current_worker.org_id)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Получить категорию по ID."""
    return await category_service.get_category_by_id(
        db, category_id, current_worker.org_id,
    )


@router.post("/", response_model=CategoryRead, status_code=201)
async def create_category(
    data: CategoryCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Создать категорию."""
    return await category_service.create_category(
        db, current_worker.org_id, data,
    )


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить категорию (частичное обновление)."""
    return await category_service.update_category(
        db, category_id, current_worker.org_id, data,
    )


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Мягкое удаление категории (ставит deleted_at)."""
    await category_service.delete_category(
        db, category_id, current_worker.org_id,
    )