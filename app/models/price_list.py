# Файл: app/models/price_list.py
# Назначение: Прайс-листы организации.
# Позволяют задавать разные цены на товары (розничные, оптовые и т.д.).
# Один прайс-лист может быть помечен как is_default.

from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class PriceList(Base):
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    """ID организации."""

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """Название прайс-листа (например, 'Розничный', 'Оптовый')."""

    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """Флаг, указывающий, что этот прайс-лист используется по умолчанию."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Активен ли прайс-лист."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    # Связи
    organization = relationship("Organization", backref="price_lists")
    items = relationship("PriceListItem", back_populates="price_list", cascade="all, delete-orphan")