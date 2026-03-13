# Файл: app/models/expense.py
# Назначение: Все расходы организации (закупки, зарплата, аренда, налоги и т.д.).
# Привязываются к конкретной точке или организации в целом.

from sqlalchemy import String, Integer, Numeric, Date, Text, ForeignKey, Enum, CheckConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import date, datetime

from app.core.database import Base


class ExpenseCategory(str, enum.Enum):
    """Категории расходов."""
    SALARY = "salary"
    PURCHASE = "purchase"
    RENT = "rent"
    TAX = "tax"
    MARKETING = "marketing"
    LOGISTICS = "logistics"
    EQUIPMENT = "equipment"
    OTHER = "other"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category", create_type=False),
        nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    point_id: Mapped[int | None] = mapped_column(
        ForeignKey("points.id", ondelete="SET NULL")
    )
    worker_payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("worker_payments.id", ondelete="SET NULL")
    )
    purchase_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchases.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now
    )

    organization = relationship("Organization")
    point = relationship("Point")
    worker_payment = relationship("WorkerPayment", back_populates="expense")
    purchase = relationship("Purchase", back_populates="expense")

    __table_args__ = (
            CheckConstraint(
                "NOT (worker_payment_id IS NOT NULL AND purchase_id IS NOT NULL)",
                name="ck_expense_one_source"
            ),
        )