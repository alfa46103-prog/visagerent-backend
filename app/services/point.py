# Файл: app/services/point.py
# Назначение: Сервис для управления точками продаж.
#
# Точка продаж — это физическое место (магазин, склад, пункт выдачи).
# К точке привязаны: остатки товаров, заказы, сотрудники, зоны доставки.
#
# Все операции фильтруются по org_id.

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.point import Point
from app.schemas import PointCreate, PointUpdate


async def get_points(
    db: AsyncSession,
    org_id: int,
    is_active: bool | None = None,
) -> list[Point]:
    """
    Получить список точек продаж организации.

    Мягко удалённые (deleted_at IS NOT NULL) не показываются.
    """
    stmt = (
        select(Point)
        .where(
            Point.org_id == org_id,
            Point.deleted_at.is_(None),
        )
    )

    if is_active is not None:
        stmt = stmt.where(Point.is_active == is_active)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_point_by_id(
    db: AsyncSession,
    point_id: int,
    org_id: int,
) -> Point:
    """Получить точку по ID с проверкой организации."""
    stmt = select(Point).where(
        Point.id == point_id,
        Point.org_id == org_id,
        Point.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    point = result.scalar_one_or_none()

    if not point:
        raise HTTPException(status_code=404, detail="Point not found")
    return point


async def create_point(
    db: AsyncSession,
    org_id: int,
    data: PointCreate,
) -> Point:
    """Создать новую точку продаж."""
    point = Point(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(point)
    await db.commit()
    await db.refresh(point)
    return point


async def update_point(
    db: AsyncSession,
    point_id: int,
    org_id: int,
    data: PointUpdate,
) -> Point:
    """Обновить точку (PATCH)."""
    point = await get_point_by_id(db, point_id, org_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(point, field, value)

    await db.commit()
    await db.refresh(point)
    return point


async def delete_point(
    db: AsyncSession,
    point_id: int,
    org_id: int,
) -> None:
    """
    Мягкое удаление точки.

    Точку нельзя удалить физически — к ней привязаны
    остатки, заказы, сотрудники. Ставим deleted_at.
    """
    point = await get_point_by_id(db, point_id, org_id)
    point.deleted_at = datetime.now(timezone.utc)
    await db.commit()