# Файл: app/models/bot_session.py
# Назначение: Сессии взаимодействия пользователя с ботом.
# Позволяет анализировать активность и поведение.

from sqlalchemy import Integer, BigInteger, JSON, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class BotSession(Base):
    __tablename__ = "bot_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    actions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    device_info: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    user = relationship("OrganizationUser", backref="bot_sessions")