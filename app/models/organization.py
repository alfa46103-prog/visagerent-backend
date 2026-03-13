# Файл: app/models/organization.py
# Назначение: Модель SQLAlchemy для таблицы organizations.
# Хранит информацию об организации-арендаторе (tenant).
# Каждая организация имеет уникальный slug (для URL), настройки в JSON,
# и флаг активности. Также содержит связи с другими таблицами.

from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base      # Base теперь берётся отсюда
from app.models.base import TimestampMixin


class Organization(Base, TimestampMixin):
    """
    Организация (тенант) в системе VisageRENT.
    Все данные в системе изолируются по org_id.
    """
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)   # Название организации
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)  # Уникальный идентификатор для URL
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default={})  # Произвольные настройки (JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # Активна ли организация

    # Связи с другими таблицами
    users = relationship("OrganizationUser", back_populates="organization", cascade="all, delete-orphan")
    points = relationship("Point", back_populates="organization", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")