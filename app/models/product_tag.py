# Файл: app/models/product_tag.py
# Назначение: Теги для товаров (например, "новинка", "хит", "акция").
# Позволяют группировать товары и применять к ним общие правила.
# Теги имеют цвет для отображения в админке.

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductTag(Base):
    __tablename__ = "product_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    """ID организации, к которой относится тег."""

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    """Название тега (например, 'Новинка')."""

    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
    """Цвет тега в HEX-формате (например, '#ff0000')."""

    # Связи
    organization = relationship("Organization", backref="product_tags")
    products = relationship("Product", secondary="product_tag_links", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_product_tag_org_name"),
    )