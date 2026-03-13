# Файл: app/models/order_item.py
# Назначение: Конкретные товары в заказе.
# Фиксирует цену и закупочную цену на момент заказа, количество, скидку.

from sqlalchemy import Integer, SmallInteger, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.sql import text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # Вычисляемое поле line_total (генерируется базой)
    line_total: Mapped[float | None] = mapped_column(Numeric(10, 2), server_default=text("0"))

    # Связи
    order = relationship("Order", back_populates="items")
    variant = relationship("ProductVariant")