# Файл: app/models/point_worker.py
# Назначение: Связующая таблица между сотрудниками и точками продаж.
# Сотрудник может работать на нескольких точках, и на точке может быть несколько сотрудников.
# Флаг is_primary указывает на основного сотрудника (например, для связи с клиентом).

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class PointWorker(Base):
    """
    Связь сотрудника с точкой продаж.
    """
    __tablename__ = "point_workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False
    )
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """Является ли сотрудник основным на этой точке (например, для отображения клиентам)."""

    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    """Дата назначения на точку."""

    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Дата снятия с точки (если сотрудник больше не работает на точке)."""

    # Связи
    point = relationship("Point", backref="workers_assigned")
    worker = relationship("Worker", back_populates="point_links")

    __table_args__ = (
        # Уникальность пары (точка, сотрудник)
        sa.UniqueConstraint("point_id", "worker_id", name="uq_point_worker"),
    )