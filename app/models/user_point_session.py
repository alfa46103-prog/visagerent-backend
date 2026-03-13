# Файл: app/models/user_point_session.py
# Назначение: Хранит текущую выбранную пользователем точку продаж.
# При входе в каталог пользователь выбирает точку, и она сохраняется здесь.

from sqlalchemy import ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class UserPointSession(Base):
    __tablename__ = "user_point_sessions"

    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="CASCADE"),
        primary_key=True
    )
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    user = relationship("OrganizationUser", backref="point_session")
    point = relationship("Point")