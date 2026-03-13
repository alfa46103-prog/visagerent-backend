# Файл: app/models/purchase.py
# Назначение: Закупка товаров у поставщика.
# Содержит общую информацию о закупке (дата, сумма, описание).

from sqlalchemy import String, Integer, Numeric, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime

from app.core.database import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL")
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    description: Mapped[str | None] = mapped_column(Text)
    invoice_path: Mapped[str | None] = mapped_column(String(255))
    json_log_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    organization = relationship("Organization")
    supplier = relationship("Supplier")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")
    expense = relationship("Expense", uselist=False, back_populates="purchase")