# Файл: app/models/worker_role.py
# Назначение: Модель для ролей сотрудников внутри организации.
# Роль определяет набор разрешений (permissions) в формате JSON.
# Например: {"can_edit_products": true, "can_view_orders": true, ...}

import sqlalchemy as sa
from sqlalchemy import String, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class WorkerRole(Base, TimestampMixin):
    """
    Роль сотрудника. Связана с организацией (org_id).
    Поле permissions хранит произвольные права в JSON.
    """
    __tablename__ = "worker_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    """ID организации, к которой относится роль."""

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    """Название роли (например, 'Администратор', 'Менеджер')."""

    description: Mapped[str | None] = mapped_column(Text)
    """Описание роли."""

    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    """JSON-объект с правами, например: {"can_edit_products": true}."""

    # Связи
    organization = relationship("Organization", backref="worker_roles", passive_deletes=True)
    workers = relationship("Worker", back_populates="role")

    __table_args__ = (
        # Название роли должно быть уникально в пределах организации
        sa.UniqueConstraint("org_id", "name", name="uq_worker_role_name"),
    )