# Файл: app/models/promotion.py
# Назначение: Акции и промокоды.
# Могут быть привязаны к конкретным товарам, категориям или ко всему заказу.
# Поддерживаются разные типы скидок (процент, фиксированная сумма, бесплатная доставка, подарок).

from sqlalchemy import String, Integer, Numeric, ForeignKey, JSON, DateTime, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.core.database import Base


class PromoType(str, enum.Enum):
    """Типы акций."""
    PERCENT = "percent"           # процентная скидка
    FIXED_RUB = "fixed_rub"       # фиксированная скидка в рублях
    FREE_SHIPPING = "free_shipping"  # бесплатная доставка
    GIFT_PRODUCT = "gift_product"    # подарок


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    promo_code: Mapped[str | None] = mapped_column(String(50), unique=True)
    promo_type: Mapped[PromoType] = mapped_column(
        Enum(PromoType, name="promo_type", create_type=False),
        nullable=False,
        default=PromoType.PERCENT
    )
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    """Значение скидки (процент или сумма)."""

    min_order: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    max_discount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    applies_to: Mapped[dict] = mapped_column(JSON, default={})
    """JSON-объект, указывающий, к чему применяется акция.
       Например: {"categories": [1,2], "products": [10,11]} или {"all": true}."""

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    # Связи
    organization = relationship("Organization", backref="promotions")
    uses = relationship("PromotionUse", back_populates="promotion", cascade="all, delete-orphan")