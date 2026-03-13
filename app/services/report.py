# Файл: app/services/report.py
# Назначение: Сервис генерации отчётов.
#
# Отчёт собирает агрегированные данные за период:
#   - выручка (сумма выполненных заказов)
#   - расходы (сумма из таблицы expenses)
#   - количество заказов
#   - новые пользователи
#
# Результат сохраняется в таблицу reports для быстрой загрузки.

from datetime import date, datetime, timezone

import csv
import io

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.report import Report, ReportType
from app.models.order import Order, OrderStatus
from app.models.expense import Expense
from app.models.organization_user import OrganizationUser
from app.schemas import ReportGenerate


async def get_reports(
    db: AsyncSession,
    org_id: int,
    report_type: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Report]:
    """Список сохранённых отчётов."""
    stmt = (
        select(Report)
        .where(Report.org_id == org_id)
        .order_by(Report.period_start.desc())
        .offset(skip)
        .limit(limit)
    )
    if report_type:
        stmt = stmt.where(Report.report_type == report_type)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def generate_report(
    db: AsyncSession,
    org_id: int,
    data: ReportGenerate,
) -> Report:
    """
    Сгенерировать отчёт за указанный период.

    Собирает данные из таблиц orders и expenses,
    сохраняет результат в reports.
    """
    period_start = date.fromisoformat(data.period_start)
    period_end = date.fromisoformat(data.period_end)

    if period_end < period_start:
        raise HTTPException(status_code=400, detail="period_end must be >= period_start")

    # Выручка — сумма total_price выполненных заказов за период
    revenue_stmt = select(func.coalesce(func.sum(Order.total_price), 0)).where(
        Order.org_id == org_id,
        Order.status == OrderStatus.COMPLETED,
        func.date(Order.created_at) >= period_start,
        func.date(Order.created_at) <= period_end,
    )
    if data.point_id:
        revenue_stmt = revenue_stmt.where(Order.point_id == data.point_id)
    revenue_result = await db.execute(revenue_stmt)
    revenue = float(revenue_result.scalar())

    # Количество заказов за период
    orders_count_stmt = select(func.count(Order.id)).where(
        Order.org_id == org_id,
        func.date(Order.created_at) >= period_start,
        func.date(Order.created_at) <= period_end,
    )
    if data.point_id:
        orders_count_stmt = orders_count_stmt.where(Order.point_id == data.point_id)
    orders_count_result = await db.execute(orders_count_stmt)
    orders_count = int(orders_count_result.scalar())

    # Расходы за период
    expenses_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.org_id == org_id,
        Expense.expense_date >= period_start,
        Expense.expense_date <= period_end,
    )
    if data.point_id:
        expenses_stmt = expenses_stmt.where(Expense.point_id == data.point_id)
    expenses_result = await db.execute(expenses_stmt)
    expenses_total = float(expenses_result.scalar())

    # Новые пользователи за период
    new_users_stmt = select(func.count(OrganizationUser.id)).where(
        OrganizationUser.org_id == org_id,
        func.date(OrganizationUser.created_at) >= period_start,
        func.date(OrganizationUser.created_at) <= period_end,
    )
    new_users_result = await db.execute(new_users_stmt)
    new_users = int(new_users_result.scalar())

    # Детали — средний чек, прибыль
    avg_check = revenue / orders_count if orders_count > 0 else 0
    profit = revenue - expenses_total

    # Сохраняем отчёт
    report = Report(
        org_id=org_id,
        report_type=data.report_type,
        period_start=period_start,
        period_end=period_end,
        point_id=data.point_id,
        revenue=revenue,
        expenses_total=expenses_total,
        orders_count=orders_count,
        new_users=new_users,
        details={
            "avg_check": round(avg_check, 2),
            "profit": round(profit, 2),
        },
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report





async def export_report_csv(
    db: AsyncSession,
    report_id: int,
    org_id: int,
) -> str:
    """
    Экспорт отчёта в CSV-формат.

    Возвращает строку CSV. Эндпоинт вернёт её как файл для скачивания.
    """
    stmt = select(Report).where(Report.id == report_id, Report.org_id == org_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    output = io.StringIO()
    writer = csv.writer(output)

    # Заголовки
    writer.writerow(["Параметр", "Значение"])
    writer.writerow(["Тип отчёта", report.report_type])
    writer.writerow(["Период", f"{report.period_start} — {report.period_end}"])
    writer.writerow(["Выручка", report.revenue])
    writer.writerow(["Расходы", report.expenses_total])
    writer.writerow(["Прибыль", report.details.get("profit", 0)])
    writer.writerow(["Кол-во заказов", report.orders_count])
    writer.writerow(["Средний чек", report.details.get("avg_check", 0)])
    writer.writerow(["Новых клиентов", report.new_users])

    return output.getvalue()