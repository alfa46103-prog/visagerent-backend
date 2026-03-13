# Файл: app/models/stock_reservation.py
# Назначение: Временные резервы товаров при добавлении в корзину.
# Живут ограниченное время (expires_at), после чего освобождаются фоновым процессом.

from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False
    )
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False
    )
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    variant = relationship("ProductVariant")
    point = relationship("Point")
    user = relationship("OrganizationUser")
    order = relationship("Order")