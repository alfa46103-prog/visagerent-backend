# Файл: app/models/global_user.py
# Назначение: Модель таблицы global_users.
# Хранит данные пользователя, общие для всех организаций (например, Telegram ID).
# Это позволяет пользователю быть зарегистрированным в нескольких организациях,
# но иметь единый профиль (имя, телефон и т.д.).

from sqlalchemy import String, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base      # Base теперь берётся отсюда
from app.models.base import TimestampMixin


class GlobalUser(Base, TimestampMixin):
    """
    Глобальный пользователь, идентифицируемый по Telegram ID.
    Может состоять в нескольких организациях (см. OrganizationUser).
    """
    __tablename__ = "global_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID пользователя
    username: Mapped[str | None] = mapped_column(String(255), index=True)  # Telegram username
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))          # Номер телефона
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})  # Доп. данные (например, языковые предпочтения)

    # Связь с членством в организациях
    organization_users = relationship("OrganizationUser", back_populates="global_user", cascade="all, delete-orphan")