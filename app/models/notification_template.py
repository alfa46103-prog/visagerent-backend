# Файл: app/models/notification_template.py
# Назначение: Шаблоны текстовых уведомлений для разных событий.
# Администратор может редактировать их через админку.

from sqlalchemy import String, Text, Boolean, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class NotificationType(str, enum.Enum):
    """Типы уведомлений."""
    ORDER_CREATED = "order_created"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_CANCELLED = "order_cancelled"
    POINTS_ACCRUED = "points_accrued"
    POINTS_EXPIRING = "points_expiring"
    PROMO = "promo"
    SYSTEM = "system"


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", create_type=False),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization", backref="notification_templates")

    __table_args__ = (
        UniqueConstraint("org_id", "type", name="uq_notification_template_org_type"),
    )