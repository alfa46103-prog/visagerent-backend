# Файл: app/models/audit_log.py
# Назначение: Журнал всех важных действий в системе.
# Используется для безопасности и разбирательств.

from sqlalchemy import (
    String, Integer, BigInteger, JSON, ForeignKey, Enum, Text, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Типы действий в аудите."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BLOCK = "block"
    UNBLOCK = "unblock"
    LOGIN = "login"
    EXPORT = "export"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id")
    )
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", create_type=False),
        nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    old_data: Mapped[dict | None] = mapped_column(JSON)
    new_data: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    organization = relationship("Organization")