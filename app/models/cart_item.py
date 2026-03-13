# Файл: app/models/cart_item.py
# Назначение: Хранение временных товаров в корзине пользователя.
# Каждая запись связывает пользователя (organization_user), вариант товара и точку.
# Цена фиксируется на момент добавления (price_snapshot), чтобы избежать изменений после добавления.

from sqlalchemy import Integer, SmallInteger, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID пользователя в организации."""

    product_variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID варианта товара."""

    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID точки продаж (для учёта остатков)."""

    quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    """Количество единиц товара (больше 0)."""

    price_snapshot: Mapped[float | None] = mapped_column(Numeric(10, 2))
    """Цена на момент добавления в корзину (может быть NULL, если не зафиксирована)."""

    # Связи (будут добавлены позже, когда появятся соответствующие модели)
    user = relationship("OrganizationUser", backref="cart_items")
    variant = relationship("ProductVariant", backref="cart_items")
    point = relationship("Point", backref="cart_items")

    __table_args__ = (
        # Один пользователь не может добавить один и тот же товар с одной точки дважды
        UniqueConstraint(
            "org_user_id", "product_variant_id", "point_id",
            name="uq_cart_item_user_variant_point"
        ),
    )