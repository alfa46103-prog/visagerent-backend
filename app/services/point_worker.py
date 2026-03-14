# Файл: app/services/point_worker.py
# Назначение:
# Привязка сотрудников к точкам внутри одной организации.
#
# Это platform-level и tenant-level полезный сервис:
# - супер-админ может управлять привязками в карточке организации
# - позже магазинная админка тоже сможет использовать те же функции

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.point import Point
from app.models.worker import Worker
from app.models.point_worker import PointWorker
from app.schemas import PointWorkerCreate


async def get_point_workers(
    db: AsyncSession,
    org_id: int,
    point_id: int,
) -> list[PointWorker]:
    """
    Получить всех сотрудников, привязанных к точке.

    Проверяем, что точка принадлежит нужной организации.
    Показываем только активные привязки (removed_at is NULL).
    """
    point_stmt = select(Point).where(
        Point.id == point_id,
        Point.org_id == org_id,
    )
    point_result = await db.execute(point_stmt)
    point = point_result.scalar_one_or_none()

    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    stmt = select(PointWorker).where(
        PointWorker.point_id == point_id,
        PointWorker.removed_at.is_(None),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def assign_worker_to_point(
    db: AsyncSession,
    org_id: int,
    point_id: int,
    data: PointWorkerCreate,
) -> PointWorker:
    """
    Привязать сотрудника к точке.

    Проверяем:
    - точка принадлежит организации
    - сотрудник принадлежит организации
    - такой активной привязки ещё нет
    """
    # Проверяем точку
    point_stmt = select(Point).where(
        Point.id == point_id,
        Point.org_id == org_id,
    )
    point_result = await db.execute(point_stmt)
    point = point_result.scalar_one_or_none()

    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    # Проверяем сотрудника
    worker_stmt = select(Worker).where(
        Worker.id == data.worker_id,
        Worker.org_id == org_id,
    )
    worker_result = await db.execute(worker_stmt)
    worker = worker_result.scalar_one_or_none()

    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Проверяем активную привязку
    existing_stmt = select(PointWorker).where(
        PointWorker.point_id == point_id,
        PointWorker.worker_id == data.worker_id,
        PointWorker.removed_at.is_(None),
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Worker is already assigned to this point",
        )

    # Если новый сотрудник становится primary —
    # снимаем primary с остальных активных привязок на этой точке
    if data.is_primary:
        current_primary_stmt = select(PointWorker).where(
            PointWorker.point_id == point_id,
            PointWorker.removed_at.is_(None),
            PointWorker.is_primary.is_(True),
        )
        current_primary_result = await db.execute(current_primary_stmt)
        current_primary_links = current_primary_result.scalars().all()

        for link in current_primary_links:
            link.is_primary = False

    link = PointWorker(
        point_id=point_id,
        worker_id=data.worker_id,
        is_primary=data.is_primary,
    )

    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def update_point_worker(
    db: AsyncSession,
    org_id: int,
    point_id: int,
    point_worker_id: int,
    is_primary: bool,
) -> PointWorker:
    """
    Обновить привязку сотрудника к точке.
    Пока поддерживаем только смену is_primary.
    """
    # Проверяем точку
    point_stmt = select(Point).where(
        Point.id == point_id,
        Point.org_id == org_id,
    )
    point_result = await db.execute(point_stmt)
    point = point_result.scalar_one_or_none()

    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    # Загружаем привязку
    stmt = select(PointWorker).where(
        PointWorker.id == point_worker_id,
        PointWorker.point_id == point_id,
        PointWorker.removed_at.is_(None),
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Point-worker link not found")

    # Если делаем текущую привязку основной —
    # сбрасываем is_primary у других активных сотрудников этой точки
    if is_primary:
        current_primary_stmt = select(PointWorker).where(
            PointWorker.point_id == point_id,
            PointWorker.removed_at.is_(None),
            PointWorker.is_primary.is_(True),
            PointWorker.id != point_worker_id,
        )
        current_primary_result = await db.execute(current_primary_stmt)
        current_primary_links = current_primary_result.scalars().all()

        for current_link in current_primary_links:
            current_link.is_primary = False

    link.is_primary = is_primary

    await db.commit()
    await db.refresh(link)
    return link


async def remove_worker_from_point(
    db: AsyncSession,
    org_id: int,
    point_id: int,
    point_worker_id: int,
) -> None:
    """
    Снять сотрудника с точки мягко:
    проставить removed_at вместо hard delete.
    """
    # Проверяем точку
    point_stmt = select(Point).where(
        Point.id == point_id,
        Point.org_id == org_id,
    )
    point_result = await db.execute(point_stmt)
    point = point_result.scalar_one_or_none()

    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    # Проверяем привязку
    stmt = select(PointWorker).where(
        PointWorker.id == point_worker_id,
        PointWorker.point_id == point_id,
        PointWorker.removed_at.is_(None),
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Point-worker link not found")

    link.removed_at = datetime.now(timezone.utc)

    # Если снимаем primary-сотрудника, просто снимаем флаг.
    # Нового primary позже можно назначить явно.
    if link.is_primary:
        link.is_primary = False

    await db.commit()