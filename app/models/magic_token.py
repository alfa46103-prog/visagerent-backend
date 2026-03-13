# Файл: app/models/magic_token.py
# Назначение: Хранение одноразовых токенов для magic-link аутентификации.
# Токен привязывается к пользователю (глобальному или организационному) и имеет срок действия.

from sqlalchemy import String, ForeignKey, DateTime, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timedelta, timezone
import secrets

from app.core.database import Base


class MagicToken(Base):
    __tablename__ = "magic_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    """Уникальный токен (генерируется автоматически)."""

    user_id: Mapped[int | None] = mapped_column(BigInteger)  # может быть global_user.id или organization_user.id
    """ID пользователя (глобального или организационного). Зависит от типа входа."""

    user_type: Mapped[str] = mapped_column(String(20), nullable=False, default="global")
    """Тип пользователя: 'global' или 'org'."""

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    """Срок действия токена."""

    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Когда токен был использован (после использования удаляется или помечается)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.token:
            self.token = secrets.token_urlsafe(48)  # генерируем случайный токен
        if not self.expires_at:
            self.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # срок жизни 24 часа

    @property
    def is_expired(self) -> bool:
        """Проверяет, истёк ли токен."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        """Проверяет, использован ли токен."""
        return self.used_at is not None