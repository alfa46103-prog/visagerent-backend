# Файл: app/services/supplier.py
# Назначение: Сервис для управления поставщиками.

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.supplier import Supplier
from app.schemas import SupplierCreate, SupplierUpdate


async def get_suppliers(
    db: AsyncSession,
    org_id: int,
) -> list[Supplier]:
    """Список поставщиков организации (без удалённых)."""
    stmt = select(Supplier).where(
        Supplier.org_id == org_id,
        Supplier.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_supplier_by_id(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
) -> Supplier:
    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.org_id == org_id,
        Supplier.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


async def create_supplier(
    db: AsyncSession,
    org_id: int,
    data: SupplierCreate,
) -> Supplier:
    supplier = Supplier(org_id=org_id, **data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def update_supplier(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
    data: SupplierUpdate,
) -> Supplier:
    supplier = await get_supplier_by_id(db, supplier_id, org_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def delete_supplier(
    db: AsyncSession,
    supplier_id: int,
    org_id: int,
) -> None:
    """Мягкое удаление — к поставщику привязаны товары и закупки."""
    supplier = await get_supplier_by_id(db, supplier_id, org_id)
    supplier.deleted_at = datetime.now(timezone.utc)
    await db.commit()