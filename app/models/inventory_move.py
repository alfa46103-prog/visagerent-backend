# Файл: app/models/inventory_move.py
# Назначение: История всех движений товаров (поступления, продажи, перемещения, списания).
# Позволяет отследить полную историю каждого товара.

from sqlalchemy import Integer, ForeignKey, String, Text, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.core.database import Base


class MoveType(str, enum.Enum):
    """Типы движений товаров."""
    PURCHASE = "purchase"       # закупка
    SALE = "sale"               # продажа
    TRANSFER_IN = "transfer_in"  # перемещение внутрь
    TRANSFER_OUT = "transfer_out"  # перемещение наружу
    ADJUSTMENT = "adjustment"   # корректировка
    WRITE_OFF = "write_off"     # списание
    RETURN = "return"           # возврат от покупателя


class InventoryMove(Base):
    __tablename__ = "inventory_moves"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False
    )
    from_point_id: Mapped[int | None] = mapped_column(ForeignKey("points.id", ondelete="RESTRICT"))
    to_point_id: Mapped[int | None] = mapped_column(ForeignKey("points.id", ondelete="RESTRICT"))
    move_type: Mapped[MoveType] = mapped_column(
        Enum(MoveType, name="move_type", create_type=False),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[int | None] = mapped_column(Integer)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("organization_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    organization = relationship("Organization")
    variant = relationship("ProductVariant")
    from_point = relationship("Point", foreign_keys=[from_point_id])
    to_point = relationship("Point", foreign_keys=[to_point_id])
    creator = relationship("OrganizationUser")