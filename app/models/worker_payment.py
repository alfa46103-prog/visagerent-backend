# Файл: app/models/worker_payment.py
# Назначение: Выплаты заработной платы сотрудникам.
# Учитываются в расходах организации.

from sqlalchemy import String, Integer, Numeric, Date, ForeignKey, Text, CheckConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime

from app.core.database import Base


class WorkerPayment(Base):
    __tablename__ = "worker_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="RESTRICT"),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    worker = relationship("Worker", back_populates="payments")
    expense = relationship("Expense", uselist=False, back_populates="worker_payment")

    __table_args__ = (
        CheckConstraint("period_end IS NULL OR period_end >= period_start", name="ck_worker_payment_period"),
    )