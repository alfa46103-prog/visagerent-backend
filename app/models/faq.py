# Файл: app/models/faq.py
# Назначение: Часто задаваемые вопросы для организации.
# Позволяет хранить вопрос, ответ, порядок сортировки и статус активности.

from sqlalchemy import String, Text, SmallInteger, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class Faq(Base, TimestampMixin):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID организации, к которой относится FAQ."""

    question: Mapped[str] = mapped_column(String(500), nullable=False)
    """Текст вопроса."""

    answer: Mapped[str] = mapped_column(Text, nullable=False)
    """Текст ответа."""

    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    """Порядок сортировки (меньше = выше)."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Активен ли вопрос (отображается ли)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now
    )

    # Связи
    organization = relationship("Organization", backref="faqs")
    """Связь с организацией (многие к одному)."""