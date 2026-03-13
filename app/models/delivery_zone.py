# Файл: app/models/delivery_zone.py
# Назначение: Зоны доставки для точки продаж.
# Содержат стоимость доставки, минимальную сумму заказа и порог бесплатной доставки.
# Поле polygon зарезервировано для геоданных (в будущем).

from sqlalchemy import String, Integer, Numeric, Boolean, JSON, ForeignKey, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeliveryZone(Base):
    """
    Зона доставки для конкретной точки.
    """
    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Название зоны (например, 'Центр', 'Северный район')."""

    min_order: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    """Минимальная сумма заказа для доставки в эту зону."""

    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    """Стоимость доставки."""

    free_from: Mapped[float | None] = mapped_column(Numeric(10, 2))
    """Сумма заказа, с которой доставка бесплатна (если задана)."""

    est_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    """Примерное время доставки в минутах."""

    polygon: Mapped[dict | None] = mapped_column(JSON)
    """Геоданные зоны (полигон) в формате GeoJSON или аналогичном (задел на будущее)."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Связи
    point = relationship("Point", backref="delivery_zones")