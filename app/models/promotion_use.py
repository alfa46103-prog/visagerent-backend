# Файл: app/models/promotion_use.py
# Назначение: Фиксация использования акции пользователем.
# Нужно для контроля лимитов (max_uses, per_user_limit).

from sqlalchemy import Integer, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class PromotionUse(Base):
    __tablename__ = "promotion_uses"

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.id", ondelete="CASCADE"),
        nullable=False
    )
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    discount_applied: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    promotion = relationship("Promotion", back_populates="uses")
    user = relationship("OrganizationUser")
    order = relationship("Order")

    __table_args__ = (
        UniqueConstraint("promotion_id", "org_user_id", "order_id", name="uq_promotion_use"),
    )