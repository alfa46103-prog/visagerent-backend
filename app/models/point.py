# Файл: app/models/point.py
# Назначение: Модель таблицы points.
# Точка продаж (магазин, склад) организации. Каждая точка имеет адрес,
# координаты, часы работы, а также флаг активности.
# На точки завязаны остатки товаров, заказы и сотрудники.

from datetime import datetime
from sqlalchemy import String, Boolean, Text, Numeric, JSON, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base      # Base теперь берётся отсюда
from app.models.base import TimestampMixin


class Point(Base, TimestampMixin):
    """
    Точка продаж (физический магазин или склад).
    """
    __tablename__ = "points"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Название точки
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)               # Текстовый адрес
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))  # Координаты для карт
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    phone: Mapped[str | None] = mapped_column(String(30))           # Контактный телефон
    work_hours: Mapped[dict] = mapped_column(JSON, default={})      # Расписание работы (JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # Для мягкого удаления

    # Связи
    organization = relationship("Organization", back_populates="points")
    # Позже добавим stock, orders, point_workers