# Файл: app/api/v1/endpoints/finance.py
# Назначение: Эндпоинты финансов: расходы, выплаты, закупки, поставщики, отчёты.

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.models.worker import Worker

from app.services.permissions import require_permission
from app.services import finance as finance_service
from app.services import supplier as supplier_service
from app.services import report as report_service
from app.schemas import (
    ExpenseCreate, ExpenseRead, ExpenseUpdate,
    WorkerPaymentCreate, WorkerPaymentRead,
    PurchaseCreate, PurchaseRead,
    SupplierCreate, SupplierRead, SupplierUpdate,
    ReportRead, ReportGenerate,
)

import io

from app.services import report as report_service

router = APIRouter()


# ── Расходы ────────────────────────────────────────────

@router.get("/expenses", response_model=list[ExpenseRead])
async def get_expenses(
    category: str | None = Query(None),
    point_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Список расходов."""
    return await finance_service.get_expenses(
        db, current_worker.org_id, category, point_id, skip, limit,
    )


@router.post("/expenses", response_model=ExpenseRead, status_code=201)
async def create_expense(
    data: ExpenseCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Создать расход."""
    return await finance_service.create_expense(db, current_worker.org_id, data)


@router.patch("/expenses/{expense_id}", response_model=ExpenseRead)
async def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить расход."""
    return await finance_service.update_expense(db, expense_id, current_worker.org_id, data)


@router.delete("/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить расход."""
    await finance_service.delete_expense(db, expense_id, current_worker.org_id)


# ── Выплаты сотрудникам ───────────────────────────────

@router.get("/payments", response_model=list[WorkerPaymentRead])
async def get_worker_payments(
    worker_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Список выплат сотрудникам."""
    return await finance_service.get_worker_payments(
        db, current_worker.org_id, worker_id, skip, limit,
    )


@router.post("/payments", response_model=WorkerPaymentRead, status_code=201)
async def create_worker_payment(
    data: WorkerPaymentCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Создать выплату (автоматически создаёт расход)."""
    return await finance_service.create_worker_payment(db, current_worker.org_id, data)


# ── Закупки ────────────────────────────────────────────

@router.get("/purchases", response_model=list[PurchaseRead])
async def get_purchases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("can_view_purchases")),
    db: AsyncSession = Depends(get_db),
):
    """Список закупок."""
    return await finance_service.get_purchases(db, current_worker.org_id, skip, limit)


@router.post("/purchases", response_model=PurchaseRead, status_code=201)
async def create_purchase(
    data: PurchaseCreate,
    current_worker: Worker = Depends(require_permission("can_create_purchases")),
    db: AsyncSession = Depends(get_db),
):
    """Создать закупку (автоматически обновляет склад и создаёт расход)."""
    return await finance_service.create_purchase(db, current_worker.org_id, data)


# ── Поставщики ─────────────────────────────────────────

@router.get("/suppliers", response_model=list[SupplierRead])
async def get_suppliers(
    current_worker: Worker = Depends(require_permission("can_view_purchases")),
    db: AsyncSession = Depends(get_db),
):
    """Список поставщиков."""
    return await supplier_service.get_suppliers(db, current_worker.org_id)


@router.post("/suppliers", response_model=SupplierRead, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    current_worker: Worker = Depends(require_permission("can_create_purchases")),
    db: AsyncSession = Depends(get_db),
):
    """Создать поставщика."""
    return await supplier_service.create_supplier(db, current_worker.org_id, data)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_worker: Worker = Depends(require_permission("can_create_purchases")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить поставщика."""
    return await supplier_service.update_supplier(db, supplier_id, current_worker.org_id, data)


@router.delete("/suppliers/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: int,
    current_worker: Worker = Depends(require_permission("can_create_purchases")),
    db: AsyncSession = Depends(get_db),
):
    """Мягкое удаление поставщика."""
    await supplier_service.delete_supplier(db, supplier_id, current_worker.org_id)


# ── Отчёты ─────────────────────────────────────────────

@router.get("/reports", response_model=list[ReportRead])
async def get_reports(
    report_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Список сохранённых отчётов."""
    return await report_service.get_reports(
        db, current_worker.org_id, report_type, skip, limit,
    )


@router.post("/reports/generate", response_model=ReportRead, status_code=201)
async def generate_report(
    data: ReportGenerate,
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Сгенерировать отчёт за период."""
    return await report_service.generate_report(db, current_worker.org_id, data)





@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: int,
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    """Скачать отчёт в формате CSV."""
    csv_content = await report_service.export_report_csv(
        db, report_id, current_worker.org_id,
    )
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"},
    )