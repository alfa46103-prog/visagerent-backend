# Файл: app/models/loyalty_program.py
# Назначение: Настройки программы лояльности для организации.
# Определяет процент начисления баллов, условия сгорания и т.д.

from sqlalchemy import String, Numeric, Integer, Boolean, ForeignKey, SmallInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class LoyaltyProgram(Base):
    __tablename__ = "loyalty_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    accrual_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=2.0)
    min_order_for_accrual: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    max_discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    min_points_for_redemption: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    points_expire_days: Mapped[int | None] = mapped_column(Integer)
    expire_check_hour: Mapped[int] = mapped_column(SmallInteger, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    organization = relationship("Organization", backref="loyalty_programs")
    transactions = relationship("LoyaltyTransaction", back_populates="program", cascade="all, delete-orphan")