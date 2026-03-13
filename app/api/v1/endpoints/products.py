# Файл: app/api/v1/endpoints/products.py
# Назначение: HTTP-эндпоинты для товаров и их вариантов.
#
# Вложенная структура URL:
#   /products/           — список товаров, создание
#   /products/{id}       — конкретный товар (с вариантами)
#   /products/{id}/variants/       — варианты товара
#   /products/{id}/variants/{vid}  — конкретный вариант

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import product as product_service

from app.schemas import (
    ProductCreate, ProductRead, ProductUpdate, ProductWithVariantsRead,
    ProductVariantCreate, ProductVariantRead, ProductVariantUpdate,
    ProductMediaCreate, ProductMediaRead
)

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ТОВАРЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/", response_model=list[ProductRead])
async def get_products(
    category_id: int | None = Query(None, description="Фильтр по категории"),
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    search: str | None = Query(None, description="Поиск по названию"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Список товаров с фильтрацией и поиском."""
    return await product_service.get_products(
        db, current_worker.org_id,
        category_id=category_id,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductWithVariantsRead)
async def get_product(
    product_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Получить товар по ID (с вариантами)."""
    return await product_service.get_product_by_id(
        db, product_id, current_worker.org_id,
    )


@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(
    data: ProductCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Создать товар."""
    return await product_service.create_product(
        db, current_worker.org_id, data,
    )


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить товар."""
    return await product_service.update_product(
        db, product_id, current_worker.org_id, data,
    )


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Мягкое удаление товара."""
    await product_service.delete_product(
        db, product_id, current_worker.org_id,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ВАРИАНТЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/{product_id}/variants", response_model=list[ProductVariantRead])
async def get_variants(
    product_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Список вариантов товара."""
    return await product_service.get_variants(
        db, product_id, current_worker.org_id,
    )


@router.post("/{product_id}/variants", response_model=ProductVariantRead, status_code=201)
async def create_variant(
    product_id: int,
    data: ProductVariantCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Создать вариант товара."""
    return await product_service.create_variant(
        db, product_id, current_worker.org_id, data,
    )


@router.patch("/{product_id}/variants/{variant_id}", response_model=ProductVariantRead)
async def update_variant(
    product_id: int,
    variant_id: int,
    data: ProductVariantUpdate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить вариант."""
    return await product_service.update_variant(
        db, variant_id, product_id, current_worker.org_id, data,
    )


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
async def delete_variant(
    product_id: int,
    variant_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Мягкое удаление варианта."""
    await product_service.delete_variant(
        db, variant_id, product_id, current_worker.org_id,
    )



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  МЕДИА
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/{product_id}/media", response_model=list[ProductMediaRead])
async def get_media(
    product_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    """Список медиафайлов товара."""
    return await product_service.get_media(db, product_id, current_worker.org_id)


@router.post("/{product_id}/media", response_model=ProductMediaRead, status_code=201)
async def add_media(
    product_id: int,
    data: ProductMediaCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Добавить фото/видео к товару."""
    return await product_service.add_media(db, product_id, current_worker.org_id, data)


@router.delete("/{product_id}/media/{media_id}", status_code=204)
async def delete_media(
    product_id: int,
    media_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить медиафайл."""
    await product_service.delete_media(db, media_id, product_id, current_worker.org_id)