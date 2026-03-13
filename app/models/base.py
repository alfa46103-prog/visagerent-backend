# Файл: app/models/base.py
# Назначение: Содержит вспомогательные миксины для моделей SQLAlchemy.
# Миксин TimestampMixin добавляет поля created_at и updated_at,
# которые автоматически заполняются при создании и обновлении записи.

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import declared_attr, Mapped, mapped_column


class TimestampMixin:
    """
    Миксин для автоматического добавления временных меток.
    - created_at: устанавливается в момент вставки (server_default)
    - updated_at: обновляется при каждом изменении (onupdate)
    """
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),  # значение по умолчанию на стороне БД
            nullable=False
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),        # обновляется при изменении строки
            nullable=False
        )