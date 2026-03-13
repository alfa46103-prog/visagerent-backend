# Файл: app/models/worker.py
# Назначение: Сотрудники организации (не путать с organization_users).
# Сотрудники имеют доступ к админке и боту сотрудника.
# Могут быть привязаны к нескольким точкам через point_workers.

from sqlalchemy import String, Boolean, Text, Date, JSON, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class Worker(Base, TimestampMixin):
    """
    Сотрудник организации. Может быть администратором, менеджером и т.д.
    Имеет Telegram ID для отправки уведомлений.
    """
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID организации."""

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Полное имя сотрудника."""

    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    """Telegram ID сотрудника (для уведомлений)."""

    telegram_username: Mapped[str | None] = mapped_column(String(100))
    """Telegram username (опционально)."""

    phone: Mapped[str | None] = mapped_column(String(30))
    """Номер телефона."""

    email: Mapped[str | None] = mapped_column(String(255))
    """Email сотрудника."""

    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("worker_roles.id", ondelete="SET NULL")
    )
    """ID роли сотрудника (может быть NULL, если роль удалена)."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Активен ли сотрудник."""

    hire_date: Mapped[date | None] = mapped_column(Date)
    """Дата найма."""

    fire_date: Mapped[date | None] = mapped_column(Date)
    """Дата увольнения (если есть)."""

    notes: Mapped[str | None] = mapped_column(Text)
    """Заметки о сотруднике."""

    extra_data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    """Дополнительные метаданные (например, настройки уведомлений)."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Дата мягкого удаления (если сотрудник удалён)."""

    # Связи
    organization = relationship("Organization", backref="workers")
    role = relationship("WorkerRole", back_populates="workers")
    point_links = relationship("PointWorker", back_populates="worker", cascade="all, delete-orphan")
    payments = relationship("WorkerPayment", back_populates="worker")