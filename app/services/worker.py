# Файл: app/services/worker.py
# Назначение: Сервис для управления сотрудниками организации.
#
# Сотрудник (Worker) — это человек, который работает в магазине.
# НЕ путать с OrganizationUser (это покупатели).
#
# Сотрудник:
#   - привязан к организации (org_id)
#   - имеет роль с правами (role_id → WorkerRole)
#   - может быть привязан к точкам продаж (через PointWorker)
#   - имеет telegram_id для получения уведомлений
#
# Все операции фильтруются по org_id — сотрудники одной
# организации не видят сотрудников другой.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.worker import Worker
from app.models.worker_role import WorkerRole
from app.schemas import WorkerCreate, WorkerUpdate


async def get_workers(
    db: AsyncSession,
    org_id: int,
    is_active: bool | None = None,
) -> list[Worker]:
    """
    Получить список сотрудников организации.

    selectinload(Worker.role) — подгружает связанную роль
    одним дополнительным запросом. Без этого при обращении
    к worker.role в async-режиме будет ошибка.

    Параметры:
        org_id: ID организации
        is_active: фильтр — True (только активные), False (уволенные), None (все)
    """
    stmt = (
        select(Worker)
        .where(Worker.org_id == org_id)
        .options(selectinload(Worker.role))  # подгружаем роль сразу
    )

    # Фильтр по активности (если передан)
    if is_active is not None:
        stmt = stmt.where(Worker.is_active == is_active)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_worker_by_id(
    db: AsyncSession,
    worker_id: int,
    org_id: int,
) -> Worker:
    """
    Получить сотрудника по ID.

    Проверяем принадлежность к организации — без этого
    можно было бы подглядывать сотрудников чужой организации.
    """
    stmt = (
        select(Worker)
        .where(
            Worker.id == worker_id,
            Worker.org_id == org_id,
        )
        .options(selectinload(Worker.role))
    )
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


async def create_worker(
    db: AsyncSession,
    org_id: int,
    data: WorkerCreate,
) -> Worker:
    """
    Создать нового сотрудника.

    Проверки:
      1. Если указан role_id — проверяем что роль существует
         и принадлежит этой организации
      2. Если указан telegram_id — проверяем уникальность
         (в модели стоит unique=True, но лучше проверить заранее
         и дать понятную ошибку)
    """
    # Проверяем роль (если указана)
    if data.role_id is not None:
        role_stmt = select(WorkerRole).where(
            WorkerRole.id == data.role_id,
            WorkerRole.org_id == org_id,
        )
        role_result = await db.execute(role_stmt)
        if not role_result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail="Role not found in this organization",
            )

    # Проверяем уникальность telegram_id (если указан)
    if data.telegram_id is not None:
        tg_stmt = select(Worker).where(Worker.telegram_id == data.telegram_id)
        tg_result = await db.execute(tg_stmt)
        if tg_result.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Worker with this telegram_id already exists",
            )

    # Создаём сотрудника
    worker = Worker(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)

    # Подгружаем роль для ответа
    # (после refresh связи не загружены, нужно запросить заново)
    return await get_worker_by_id(db, worker.id, org_id)


async def update_worker(
    db: AsyncSession,
    worker_id: int,
    org_id: int,
    data: WorkerUpdate,
) -> Worker:
    """
    Обновить данные сотрудника (PATCH).

    Если меняется role_id — проверяем что новая роль
    принадлежит этой организации.
    """
    worker = await get_worker_by_id(db, worker_id, org_id)

    update_data = data.model_dump(exclude_unset=True)

    # Если меняют роль — проверяем что она из нашей организации
    if "role_id" in update_data and update_data["role_id"] is not None:
        role_stmt = select(WorkerRole).where(
            WorkerRole.id == update_data["role_id"],
            WorkerRole.org_id == org_id,
        )
        role_result = await db.execute(role_stmt)
        if not role_result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail="Role not found in this organization",
            )

    # Обновляем поля
    for field, value in update_data.items():
        setattr(worker, field, value)

    await db.commit()

    # Перезагружаем с ролью
    return await get_worker_by_id(db, worker.id, org_id)


async def deactivate_worker(
    db: AsyncSession,
    worker_id: int,
    org_id: int,
) -> Worker:
    """
    Деактивировать (уволить) сотрудника.

    Не удаляем из БД — ставим is_active = False.
    Это мягкое удаление: данные сохраняются для истории
    (аудит, старые заказы привязаны к сотрудникам).
    """
    worker = await get_worker_by_id(db, worker_id, org_id)
    worker.is_active = False
    await db.commit()
    return await get_worker_by_id(db, worker.id, org_id)