# Файл: app/models/product_tag_link.py
# Назначение: Связующая таблица между товарами и тегами (many-to-many).

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductTagLink(Base):
    __tablename__ = "product_tag_links"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("product_tags.id", ondelete="CASCADE"),
        primary_key=True
    )

    product = relationship("Product", backref="tag_links")
    tag = relationship("ProductTag", backref="product_links")