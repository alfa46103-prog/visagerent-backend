# Файл: app/models/notification_queue.py
# Назначение: Очередь уведомлений для асинхронной отправки.
# Celery worker будет забирать отсюда записи и отправлять уведомления.

from sqlalchemy import (
    Integer, BigInteger, JSON, ForeignKey, Enum, DateTime, Text, SmallInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from app.models.notification_template import NotificationType


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        nullable=False
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("notification_templates.id")
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", create_type=False),
        nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSON, default={})
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    organization = relationship("Organization")
    user = relationship("OrganizationUser")
    template = relationship("NotificationTemplate")