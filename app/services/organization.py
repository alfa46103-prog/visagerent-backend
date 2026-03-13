# Файл: app/services/organization.py
# Назначение: Сервис для работы с организациями.
#
# Содержит всю бизнес-логику: создание, обновление, удаление,
# получение списка организаций.
#
# Эндпоинты (и в будущем бот) вызывают методы этого сервиса,
# а не работают с БД напрямую. Это позволяет:
#   - не дублировать логику между API и ботом
#   - легко писать тесты (мокаем сервис, а не всю БД)
#   - держать эндпоинты тонкими и читаемыми

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.organization import Organization
from app.schemas import OrganizationCreate, OrganizationUpdate

from sqlalchemy import delete
from app.models.worker_role import WorkerRole


async def get_organizations(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
) -> list[Organization]:
    """
    Получить список организаций с пагинацией и фильтрацией.

    Параметры:
        db: сессия базы данных
        skip: сколько записей пропустить (для пагинации)
        limit: максимум записей в ответе
        is_active: фильтр по активности (None = все)

    Возвращает:
        Список объектов Organization
    """
    # Базовый запрос: SELECT * FROM organizations
    stmt = select(Organization).offset(skip).limit(limit)

    # Если передан фильтр — добавляем WHERE is_active = ...
    if is_active is not None:
        stmt = stmt.where(Organization.is_active == is_active)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_organization_by_id(
    db: AsyncSession,
    org_id: int,
) -> Organization:
    """
    Получить организацию по ID.

    Если не найдена — выбрасывает HTTPException 404.
    """
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def create_organization(
    db: AsyncSession,
    data: OrganizationCreate,
) -> Organization:
    """
    Создать новую организацию.

    При создании автоматически создаются три дефолтных роли
    (Администратор, Менеджер, Кладовщик) — см. worker_role.create_default_roles.
    """
    # Проверяем уникальность slug
    existing = await db.execute(
        select(Organization).where(Organization.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Organization with slug '{data.slug}' already exists"
        )

    # Создаём организацию
    org = Organization(**data.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)

    # Создаём дефолтные роли для новой организации
    from app.services.worker_role import create_default_roles
    await create_default_roles(db, org.id)

    return org


async def update_organization(
    db: AsyncSession,
    org_id: int,
    data: OrganizationUpdate,
) -> Organization:
    """
    Частичное обновление организации (PATCH).

    exclude_unset=True означает: если поле не передано в запросе,
    оно НЕ будет обновлено. Например, если прислали только {"name": "New"},
    то slug и остальные поля останутся прежними.
    """
    # Сначала находим организацию (или 404)
    org = await get_organization_by_id(db, org_id)

    # Берём только те поля, которые реально были переданы в запросе
    update_data = data.model_dump(exclude_unset=True)

    # Обновляем каждое переданное поле
    for field, value in update_data.items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return org


async def delete_organization(
    db: AsyncSession,
    org_id: int,
) -> None:
    """
    Удалить организацию по ID.

    Сначала удаляем все связанные роли (WorkerRole),
    затем организацию. Это обходит ограничение NOT NULL в SQLite.
    """
    # 1. Удаляем все роли этой организации
    await db.execute(
        delete(WorkerRole).where(WorkerRole.org_id == org_id)
    )
    # 2. Удаляем саму организацию
    org = await get_organization_by_id(db, org_id)
    await db.delete(org)
    # 3. Фиксируем изменения
    await db.commit()