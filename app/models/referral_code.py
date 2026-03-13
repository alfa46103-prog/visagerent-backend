# Файл: app/models/referral_code.py
# Назначение: Реферальные коды пользователей.
# Генерируются автоматически, могут иметь ограничение по использованию и срок действия.

from sqlalchemy import String, Integer, Numeric, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    bonus_points: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    new_user_bonus: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    user = relationship("OrganizationUser", backref="referral_codes")