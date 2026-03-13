# Файл: app/models/stock.py
# Назначение: Остатки товаров на точках продаж.
# Содержит фактическое количество, зарезервированное количество, минимальный порог.

from sqlalchemy import Integer, ForeignKey, CheckConstraint, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class Stock(Base):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False
    )
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Фактическое количество на складе."""

    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Количество, зарезервированное в текущих корзинах."""

    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Порог низкого остатка (для уведомлений)."""

    deeplink: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)

    variant = relationship("ProductVariant", backref="stocks")
    point = relationship("Point", backref="stocks")

    __table_args__ = (
        UniqueConstraint("product_variant_id", "point_id", name="uq_stock_variant_point"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_positive"),
        CheckConstraint("reserved_quantity >= 0", name="ck_stock_reserved_positive"),
        CheckConstraint("quantity >= reserved_quantity", name="ck_stock_quantity_ge_reserved"),
    )