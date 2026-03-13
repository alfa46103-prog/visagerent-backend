# Файл: app/services/finance.py
# Назначение: Сервис финансов — расходы, выплаты сотрудникам, закупки.
#
# Закупка (Purchase) при сохранении автоматически:
#   1. Создаёт запись расхода (Expense) с категорией "purchase"
#   2. Увеличивает остатки (Stock) на указанных точках
#   3. Записывает движения (InventoryMove) с типом "purchase"
#
# Выплата (WorkerPayment) автоматически создаёт расход с категорией "salary".

from datetime import date, datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.expense import Expense, ExpenseCategory
from app.models.worker_payment import WorkerPayment
from app.models.worker import Worker
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.stock import Stock
from app.models.inventory_move import InventoryMove, MoveType
from app.models.point import Point
from app.schemas import (
    ExpenseCreate, ExpenseUpdate,
    WorkerPaymentCreate,
    PurchaseCreate,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  РАСХОДЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_expenses(
    db: AsyncSession,
    org_id: int,
    category: str | None = None,
    point_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Expense]:
    """Список расходов с фильтрацией."""
    stmt = (
        select(Expense)
        .where(Expense.org_id == org_id)
        .order_by(Expense.expense_date.desc())
        .offset(skip)
        .limit(limit)
    )
    if category:
        stmt = stmt.where(Expense.category == category)
    if point_id:
        stmt = stmt.where(Expense.point_id == point_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_expense(
    db: AsyncSession,
    org_id: int,
    data: ExpenseCreate,
) -> Expense:
    """Создать расход вручную."""
    expense = Expense(
        org_id=org_id,
        amount=data.amount,
        category=data.category,
        description=data.description,
        point_id=data.point_id,
        expense_date=date.fromisoformat(data.expense_date) if data.expense_date else date.today(),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


async def update_expense(
    db: AsyncSession,
    expense_id: int,
    org_id: int,
    data: ExpenseUpdate,
) -> Expense:
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.org_id == org_id,
    )
    result = await db.execute(stmt)
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)

    await db.commit()
    await db.refresh(expense)
    return expense


async def delete_expense(
    db: AsyncSession,
    expense_id: int,
    org_id: int,
) -> None:
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.org_id == org_id,
    )
    result = await db.execute(stmt)
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.delete(expense)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ВЫПЛАТЫ СОТРУДНИКАМ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_worker_payments(
    db: AsyncSession,
    org_id: int,
    worker_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[WorkerPayment]:
    """Список выплат. Можно фильтровать по сотруднику."""
    stmt = (
        select(WorkerPayment)
        .join(Worker, WorkerPayment.worker_id == Worker.id)
        .where(Worker.org_id == org_id)
        .order_by(WorkerPayment.payment_date.desc())
        .offset(skip)
        .limit(limit)
    )
    if worker_id:
        stmt = stmt.where(WorkerPayment.worker_id == worker_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_worker_payment(
    db: AsyncSession,
    org_id: int,
    data: WorkerPaymentCreate,
) -> WorkerPayment:
    """
    Создать выплату сотруднику.
    Автоматически создаёт расход с категорией "salary".
    """
    # Проверяем что сотрудник из нашей организации
    worker = await db.get(Worker, data.worker_id)
    if not worker or worker.org_id != org_id:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Создаём выплату
    payment = WorkerPayment(
        worker_id=data.worker_id,
        amount=data.amount,
        payment_date=date.fromisoformat(data.payment_date) if data.payment_date else date.today(),
        period_start=date.fromisoformat(data.period_start) if data.period_start else None,
        period_end=date.fromisoformat(data.period_end) if data.period_end else None,
        description=data.description,
    )
    db.add(payment)
    await db.flush()  # получаем payment.id

    # Автоматически создаём расход
    expense = Expense(
        org_id=org_id,
        amount=data.amount,
        category=ExpenseCategory.SALARY,
        description=f"Зарплата: {worker.full_name}",
        worker_payment_id=payment.id,
        expense_date=payment.payment_date,
    )
    db.add(expense)

    await db.commit()
    await db.refresh(payment)
    return payment


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ЗАКУПКИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_purchases(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[Purchase]:
    """Список закупок с позициями."""
    stmt = (
        select(Purchase)
        .where(Purchase.org_id == org_id)
        .options(selectinload(Purchase.items))
        .order_by(Purchase.purchase_date.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def create_purchase(
    db: AsyncSession,
    org_id: int,
    data: PurchaseCreate,
) -> Purchase:
    """
    Создать закупку.

    При сохранении автоматически:
      1. Считает общую сумму по позициям
      2. Увеличивает остатки на указанных точках
      3. Записывает движения товаров (inventory_moves)
      4. Создаёт расход с категорией "purchase"
    """
    if not data.items:
        raise HTTPException(status_code=400, detail="Purchase must have at least one item")

    # Считаем общую сумму
    total_amount = sum(item.quantity * item.price for item in data.items)

    # Создаём закупку
    purchase = Purchase(
        org_id=org_id,
        supplier_id=data.supplier_id,
        amount=total_amount,
        purchase_date=date.fromisoformat(data.purchase_date) if data.purchase_date else date.today(),
        description=data.description,
    )
    db.add(purchase)
    await db.flush()  # получаем purchase.id

    # Создаём позиции и обновляем остатки
    for item_data in data.items:
        # Позиция закупки
        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            product_variant_id=item_data.product_variant_id,
            point_id=item_data.point_id,
            quantity=item_data.quantity,
            price=item_data.price,
        )
        db.add(purchase_item)

        # Обновляем остаток на точке
        stock_stmt = select(Stock).where(
            Stock.product_variant_id == item_data.product_variant_id,
            Stock.point_id == item_data.point_id,
        )
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()

        if stock:
            # Запись уже есть — увеличиваем количество
            stock.quantity += item_data.quantity
        else:
            # Первая поставка на эту точку — создаём запись
            stock = Stock(
                product_variant_id=item_data.product_variant_id,
                point_id=item_data.point_id,
                quantity=item_data.quantity,
            )
            db.add(stock)

        # Записываем движение: поступление
        move = InventoryMove(
            org_id=org_id,
            product_variant_id=item_data.product_variant_id,
            to_point_id=item_data.point_id,
            move_type=MoveType.PURCHASE,
            quantity=item_data.quantity,
            reference_id=purchase.id,
            reference_type="purchase",
        )
        db.add(move)

    # Создаём расход
    expense = Expense(
        org_id=org_id,
        amount=total_amount,
        category=ExpenseCategory.PURCHASE,
        description=data.description or "Закупка товаров",
        purchase_id=purchase.id,
        expense_date=purchase.purchase_date,
    )
    db.add(expense)

    await db.commit()

    # Перезагружаем с позициями
    stmt = (
        select(Purchase)
        .where(Purchase.id == purchase.id)
        .options(selectinload(Purchase.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one()