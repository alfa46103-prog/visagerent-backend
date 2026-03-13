# Файл: app/services/product.py
# Назначение: Сервис для управления товарами и их вариантами.
#
# Товар (Product) — карточка товара с названием, описанием, фото.
# Вариант (ProductVariant) — конкретная версия товара с ценой.
# Например, товар "Elfbar" может иметь варианты:
#   - "Клубника" — 500₽
#   - "Манго" — 500₽
#   - "Мята" — 450₽
#
# Один товар → много вариантов. Покупатель добавляет в корзину
# именно вариант (а не товар).
#
# Все операции фильтруются по org_id — мультитенантность.

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.product import Product, ProductVariant
from app.models.category import Category
from app.schemas import (
    ProductCreate, ProductUpdate,
    ProductVariantCreate, ProductVariantUpdate,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ТОВАРЫ (Product)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_products(
    db: AsyncSession,
    org_id: int,
    category_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Product]:
    """
    Получить список товаров организации.

    Параметры:
        category_id: фильтр по категории
        is_active: фильтр по активности
        search: поиск по названию (ILIKE — регистронезависимый)
        skip/limit: пагинация
    """
    stmt = (
        select(Product)
        .where(
            Product.org_id == org_id,
            Product.deleted_at.is_(None),  # не показываем мягко удалённые
        )
        .order_by(Product.priority)
        .offset(skip)
        .limit(limit)
    )

    # Фильтр по категории
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    # Фильтр по активности
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)

    # Поиск по названию
    # ILIKE — регистронезависимый LIKE (только PostgreSQL)
    # % по краям означает поиск подстроки в любом месте названия
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_product_by_id(
    db: AsyncSession,
    product_id: int,
    org_id: int,
) -> Product:
    """
    Получить товар по ID с подгруженными вариантами.

    selectinload(Product.variants) — загружает все варианты
    одним дополнительным SQL-запросом. Без этого обращение
    к product.variants в async-режиме вызовет ошибку.
    """
    stmt = (
        select(Product)
        .where(
            Product.id == product_id,
            Product.org_id == org_id,
            Product.deleted_at.is_(None),
        )
        .options(selectinload(Product.variants))
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


async def create_product(
    db: AsyncSession,
    org_id: int,
    data: ProductCreate,
) -> Product:
    """
    Создать новый товар.

    Проверяем что указанная категория существует
    и принадлежит этой организации.
    """
    # Проверяем категорию
    cat_stmt = select(Category).where(
        Category.id == data.category_id,
        Category.org_id == org_id,
        Category.deleted_at.is_(None),
    )
    cat_result = await db.execute(cat_stmt)
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession,
    product_id: int,
    org_id: int,
    data: ProductUpdate,
) -> Product:
    """
    Обновить товар (PATCH).

    Если меняется category_id — проверяем что новая категория
    существует в нашей организации.
    """
    product = await get_product_by_id(db, product_id, org_id)

    update_data = data.model_dump(exclude_unset=True)

    # Проверяем новую категорию (если меняется)
    if "category_id" in update_data:
        cat_stmt = select(Category).where(
            Category.id == update_data["category_id"],
            Category.org_id == org_id,
            Category.deleted_at.is_(None),
        )
        cat_result = await db.execute(cat_stmt)
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Category not found")

    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    return await get_product_by_id(db, product_id, org_id)


async def delete_product(
    db: AsyncSession,
    product_id: int,
    org_id: int,
) -> None:
    """
    Мягкое удаление товара.

    Ставим deleted_at — товар перестаёт отображаться,
    но остаётся в БД для истории заказов.
    """
    product = await get_product_by_id(db, product_id, org_id)
    product.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ВАРИАНТЫ (ProductVariant)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_variants(
    db: AsyncSession,
    product_id: int,
    org_id: int,
) -> list[ProductVariant]:
    """
    Получить все варианты товара.

    Сначала проверяем что товар существует и принадлежит
    нашей организации (через get_product_by_id).
    """
    # Проверяем что товар наш
    await get_product_by_id(db, product_id, org_id)

    stmt = (
        select(ProductVariant)
        .where(
            ProductVariant.product_id == product_id,
            ProductVariant.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_variant_by_id(
    db: AsyncSession,
    variant_id: int,
    product_id: int,
    org_id: int,
) -> ProductVariant:
    """
    Получить вариант по ID.

    Тройная проверка:
      1. Товар принадлежит организации
      2. Вариант принадлежит этому товару
      3. Вариант не удалён
    """
    # Проверяем что товар наш
    await get_product_by_id(db, product_id, org_id)

    stmt = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id,
        ProductVariant.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    variant = result.scalar_one_or_none()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant


async def create_variant(
    db: AsyncSession,
    product_id: int,
    org_id: int,
    data: ProductVariantCreate,
) -> ProductVariant:
    """
    Создать вариант товара.

    Проверяем уникальность variant_key в пределах товара.
    Например, у товара "Elfbar" не может быть двух вариантов
    с ключом "strawberry".
    """
    # Проверяем что товар наш
    await get_product_by_id(db, product_id, org_id)

    # Проверяем уникальность variant_key
    existing = await db.execute(
        select(ProductVariant).where(
            ProductVariant.product_id == product_id,
            ProductVariant.variant_key == data.variant_key,
            ProductVariant.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Variant with key '{data.variant_key}' already exists",
        )

    variant = ProductVariant(
        product_id=product_id,
        **data.model_dump(),
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant


async def update_variant(
    db: AsyncSession,
    variant_id: int,
    product_id: int,
    org_id: int,
    data: ProductVariantUpdate,
) -> ProductVariant:
    """Обновить вариант (PATCH)."""
    variant = await get_variant_by_id(db, variant_id, product_id, org_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variant, field, value)

    await db.commit()
    await db.refresh(variant)
    return variant


async def delete_variant(
    db: AsyncSession,
    variant_id: int,
    product_id: int,
    org_id: int,
) -> None:
    """Мягкое удаление варианта."""
    variant = await get_variant_by_id(db, variant_id, product_id, org_id)
    variant.deleted_at = datetime.now(timezone.utc)
    await db.commit()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  МЕДИА (ProductMedia)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from app.models.product_media import ProductMedia


async def get_media(
    db: AsyncSession,
    product_id: int,
    org_id: int,
) -> list[ProductMedia]:
    """Все медиафайлы товара, отсортированные по position."""
    await get_product_by_id(db, product_id, org_id)
    stmt = (
        select(ProductMedia)
        .where(ProductMedia.product_id == product_id)
        .order_by(ProductMedia.position)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_media(
    db: AsyncSession,
    product_id: int,
    org_id: int,
    data,
) -> ProductMedia:
    """Добавить фото/видео к товару."""
    await get_product_by_id(db, product_id, org_id)
    media = ProductMedia(product_id=product_id, **data.model_dump())
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


async def delete_media(
    db: AsyncSession,
    media_id: int,
    product_id: int,
    org_id: int,
) -> None:
    """Удалить медиафайл."""
    await get_product_by_id(db, product_id, org_id)
    stmt = select(ProductMedia).where(
        ProductMedia.id == media_id,
        ProductMedia.product_id == product_id,
    )
    result = await db.execute(stmt)
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    await db.delete(media)
    await db.commit()