# Файл: app/models/supplier.py
# Назначение: Модель для поставщиков (suppliers).
# Хранит информацию о поставщиках товаров для организации.

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class Supplier(Base, TimestampMixin):
    """
    Модель поставщика.
    Связана с организацией (org_id). Может быть мягко удалена (deleted_at).
    """
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Уникальный идентификатор поставщика (первичный ключ)."""

    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID организации, к которой относится поставщик. Внешний ключ на organizations.id."""

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Название компании-поставщика."""

    contact: Mapped[str | None] = mapped_column(String(255))
    """Контактное лицо (имя, должность)."""

    phone: Mapped[str | None] = mapped_column(String(30))
    """Телефон поставщика."""

    email: Mapped[str | None] = mapped_column(String(255))
    """Email поставщика."""

    notes: Mapped[str | None] = mapped_column(Text)
    """Произвольные заметки о поставщике."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Дата и время мягкого удаления записи. Если не NULL — поставщик считается удалённым."""

    # Связи
    organization = relationship("Organization", backref="suppliers")
    """Связь с организацией (многие к одному)."""

    products = relationship("Product", back_populates="supplier")
    """Список товаров этого поставщика (связь один ко многим)."""