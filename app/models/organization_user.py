# Файл: app/models/organization_user.py
# Назначение: Связующая таблица между global_users и organizations.
# Хранит роль пользователя в конкретной организации, статус блокировки,
# реферальные связи, уровень лояльности и статистику заказов.
# Это ключевая таблица для мультитенантности.

import enum
import sqlalchemy as sa
from sqlalchemy import Integer, BigInteger, Boolean, Text, Numeric, JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from app.core.database import Base      # Base теперь берётся отсюда
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    """Возможные роли пользователя внутри организации."""
    USER = "user"          # обычный покупатель
    ADMIN = "admin"        # администратор магазина
    MODERATOR = "moderator"  # модератор/менеджер


class OrganizationUser(Base, TimestampMixin):
    """
    Членство пользователя в организации.
    Содержит все данные, специфичные для конкретной организации.
    """
    __tablename__ = "organization_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # внутренний ID (BIGSERIAL)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("global_users.id", ondelete="CASCADE"), nullable=False)

    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.USER)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    block_reason: Mapped[str | None] = mapped_column(Text)

    # Реферальная система
    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("organization_users.id", ondelete="SET NULL"))
    tier_id: Mapped[int | None] = mapped_column(ForeignKey("loyalty_tiers.id", ondelete="SET NULL"))

    # Сумма всех завершённых заказов (используется для определения уровня лояльности)
    total_orders_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Произвольные метаданные (например, избранные товары)
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    # Связи
    organization = relationship("Organization", back_populates="users")
    global_user = relationship("GlobalUser", back_populates="organization_users")
    referrer = relationship("OrganizationUser", remote_side=[id], backref="referrals")
    tier = relationship("LoyaltyTier", backref="users")  # будет добавлено позже

    # Уникальность пары (организация, пользователь) — один пользователь не может дважды состоять в одной организации
    __table_args__ = (
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_user"),
    )