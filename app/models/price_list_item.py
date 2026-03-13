# Файл: app/models/price_list_item.py
# Назначение: Связь варианта товара с ценой в конкретном прайс-листе.
# Позволяет задавать цену, период действия (valid_from, valid_until).

from sqlalchemy import Integer, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class PriceListItem(Base):
    __tablename__ = "price_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    price_list_id: Mapped[int] = mapped_column(
        ForeignKey("price_lists.id", ondelete="CASCADE"),
        nullable=False
    )
    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False
    )
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    """Цена варианта в этом прайс-листе."""

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Связи
    price_list = relationship("PriceList", back_populates="items")
    variant = relationship("ProductVariant")

    __table_args__ = (
        UniqueConstraint("price_list_id", "product_variant_id", name="uq_price_list_variant"),
    )