# Файл: app/models/link.py
# Назначение: Хранит полезные ссылки для организации (например, на документацию, соцсети).
# Могут отображаться в боте или админке.

from sqlalchemy import String, Text, SmallInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class Link(Base, TimestampMixin):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization", backref="links")