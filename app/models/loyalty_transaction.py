# Файл: app/models/loyalty_transaction.py
# Назначение: Движения баллов пользователя (начисление, списание, сгорание).
# Ведёт баланс и контроль срока действия баллов.

from sqlalchemy import (
    Integer, Numeric, ForeignKey, String, DateTime, Boolean, Enum, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.core.database import Base


class LoyaltyTxType(str, enum.Enum):
    """Типы транзакций баллов."""
    ORDER_ACCRUAL = "order_accrual"
    REDEMPTION = "redemption"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    EXPIRATION = "expiration"
    REFERRAL_BONUS = "referral_bonus"
    TIER_BONUS = "tier_bonus"
    PROMO_BONUS = "promo_bonus"
    REFUND = "refund"


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("loyalty_programs.id", ondelete="RESTRICT"),
        nullable=False
    )
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL")
    )
    points: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    available_points: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    type: Mapped[LoyaltyTxType] = mapped_column(
        Enum(LoyaltyTxType, name="loyalty_tx_type", create_type=False),
        nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    organization = relationship("Organization")
    program = relationship("LoyaltyProgram", back_populates="transactions")
    user = relationship("OrganizationUser", backref="loyalty_transactions")
    order = relationship("Order")

    __table_args__ = (
        CheckConstraint(
            "(points > 0 AND available_points >= 0) OR (points <= 0 AND available_points = 0)",
            name="ck_loyalty_points_consistency"
        ),
    )