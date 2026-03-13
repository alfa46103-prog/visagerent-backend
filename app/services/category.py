# Файл: app/services/category.py
# Назначение: Сервис для управления категориями товаров.
#
# Категории поддерживают вложенность (parent_id) и мягкое удаление (deleted_at).
# Все операции фильтруются по org_id — мультитенантность.
#
# Основные возможности:
#   - CRUD (создание, чтение, обновление, удаление)
#   - Получение дерева категорий (для бота и админки)
#   - Мягкое удаление (deleted_at вместо физического удаления)

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.category import Category
from app.schemas import CategoryCreate, CategoryUpdate, CategoryTreeRead


async def get_categories(
    db: AsyncSession,
    org_id: int,
    is_active: bool | None = None,
    parent_id: int | None = None,
    include_deleted: bool = False,
) -> list[Category]:
    """
    Получить список категорий организации.

    Параметры:
        org_id: ID организации
        is_active: фильтр по активности (None = все)
        parent_id: фильтр по родителю (None = корневые категории)
        include_deleted: показывать ли мягко удалённые

    Результат отсортирован по priority (меньше = выше).
    """
    stmt = (
        select(Category)
        .where(Category.org_id == org_id)
        .order_by(Category.priority)  # сортировка по приоритету
    )

    # Фильтр по активности
    if is_active is not None:
        stmt = stmt.where(Category.is_active == is_active)

    # Не показываем мягко удалённые (по умолчанию)
    if not include_deleted:
        stmt = stmt.where(Category.deleted_at.is_(None))

    # Фильтр по родителю
    # parent_id=None в запросе означает "только корневые" (без родителя)
    if parent_id is not None:
        stmt = stmt.where(Category.parent_id == parent_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_id(
    db: AsyncSession,
    category_id: int,
    org_id: int,
) -> Category:
    """
    Получить категорию по ID.
    Проверяет принадлежность к организации и что не удалена.
    """
    stmt = select(Category).where(
        Category.id == category_id,
        Category.org_id == org_id,
        Category.deleted_at.is_(None),  # не показываем удалённые
    )
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


async def create_category(
    db: AsyncSession,
    org_id: int,
    data: CategoryCreate,
) -> Category:
    """
    Создать новую категорию.

    Если указан parent_id — проверяем что родительская категория
    существует и принадлежит этой же организации.
    """
    # Проверяем родительскую категорию (если указана)
    if data.parent_id is not None:
        parent = await db.execute(
            select(Category).where(
                Category.id == data.parent_id,
                Category.org_id == org_id,
                Category.deleted_at.is_(None),
            )
        )
        if not parent.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail="Parent category not found",
            )

    category = Category(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    category_id: int,
    org_id: int,
    data: CategoryUpdate,
) -> Category:
    """
    Обновить категорию (PATCH).

    Если меняется parent_id — проверяем что:
      1. Новый родитель существует в нашей организации
      2. Категория не назначается родителем сама себе
    """
    category = await get_category_by_id(db, category_id, org_id)

    update_data = data.model_dump(exclude_unset=True)

    # Проверяем нового родителя (если меняется)
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]

        # Нельзя назначить саму себя родителем
        if new_parent_id == category_id:
            raise HTTPException(
                status_code=400,
                detail="Category cannot be its own parent",
            )

        # Проверяем что новый родитель существует
        if new_parent_id is not None:
            parent = await db.execute(
                select(Category).where(
                    Category.id == new_parent_id,
                    Category.org_id == org_id,
                    Category.deleted_at.is_(None),
                )
            )
            if not parent.scalar_one_or_none():
                raise HTTPException(
                    status_code=404,
                    detail="Parent category not found",
                )

    # Применяем изменения
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(
    db: AsyncSession,
    category_id: int,
    org_id: int,
) -> None:
    """
    Мягкое удаление категории.

    Не удаляем из БД — ставим deleted_at = текущее время.
    Это нужно потому что к категории привязаны товары,
    а к товарам — заказы. Физическое удаление сломало бы историю.

    Товары в этой категории остаются, но в боте категория
    не будет отображаться (фильтр deleted_at IS NULL).
    """
    category = await get_category_by_id(db, category_id, org_id)
    category.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def get_category_tree(
    db: AsyncSession,
    org_id: int,
) -> list[CategoryTreeRead]:
    """
    Построить дерево категорий для отображения в боте и админке.

    Алгоритм:
      1. Загружаем ВСЕ активные категории организации одним запросом
      2. Группируем по parent_id в словарь
      3. Рекурсивно собираем дерево начиная с корневых (parent_id IS NULL)

    Возвращает список корневых категорий, у каждой — поле children
    с вложенными подкатегориями.
    """
    # Загружаем все активные неудалённые категории
    stmt = (
        select(Category)
        .where(
            Category.org_id == org_id,
            Category.is_active == True,
            Category.deleted_at.is_(None),
        )
        .order_by(Category.priority)
    )
    result = await db.execute(stmt)
    all_categories = list(result.scalars().all())

    # Группируем по parent_id: {parent_id: [cat1, cat2, ...]}
    children_map: dict[int | None, list[Category]] = {}
    for cat in all_categories:
        parent = cat.parent_id
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(cat)

    def build_tree(parent_id: int | None) -> list[CategoryTreeRead]:
        """Рекурсивно строит дерево из словаря."""
        nodes = children_map.get(parent_id, [])
        result = []
        for node in nodes:
            tree_node = CategoryTreeRead.model_validate(node)
            # Рекурсивно добавляем дочерние категории
            tree_node.children = build_tree(node.id)
            result.append(tree_node)
        return result

    # Начинаем с корневых категорий (parent_id = None)
    return build_tree(None)