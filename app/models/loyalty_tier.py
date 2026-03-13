# Файл: app/models/loyalty_tier.py
# Назначение: Модель для уровней лояльности (loyalty_tiers).
# Каждый уровень связан с организацией, имеет минимальную сумму покупок,
# множитель начисления баллов, процент скидки и другие параметры.

from sqlalchemy import String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class LoyaltyTier(Base, TimestampMixin):
    __tablename__ = "loyalty_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_orders_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    accrual_multiplier: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    color_hex: Mapped[str | None] = mapped_column(String(7), default="#94a3b8")
    icon_emoji: Mapped[str | None] = mapped_column(String(10))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Связи
    organization = relationship("Organization", backref="loyalty_tiers")