# Файл: app/models/order_status_history.py
# Назначение: Логирование изменений статуса заказа.
# Используется для аудита и отображения хронологии заказа.

from sqlalchemy import Integer, ForeignKey, Text, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from app.models.order import OrderStatus


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    old_status: Mapped[OrderStatus | None] = mapped_column(
        Enum(OrderStatus, name="order_status", create_type=False)
    )
    new_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", create_type=False),
        nullable=False
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("organization_users.id", ondelete="SET NULL")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    order = relationship("Order", back_populates="status_history")
    changer = relationship("OrganizationUser")