# Файл: app/models/category.py
# Назначение: Модель таблицы categories.
# Категории товаров (могут быть вложенными). Содержат название, эмодзи,
# приоритет сортировки, а также метки для вариантов (например, "Вкус", "Крепость").

from datetime import datetime
from sqlalchemy import String, Boolean, Text, SmallInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base      # Base теперь берётся отсюда
from app.models.base import TimestampMixin


class Category(Base, TimestampMixin):
    """
    Категория товаров. Может иметь родительскую категорию (parent_id).
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Название категории
    slug: Mapped[str | None] = mapped_column(String(255))           # Уникальный идентификатор для ссылок
    emoji: Mapped[str | None] = mapped_column(String(10))           # Эмодзи для отображения в боте
    description: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(255))     # Путь к изображению
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)  # Сортировка (меньше = выше)

    # Поля для настройки отображения вариантов (например, "Выберите вкус")
    variant_label: Mapped[str | None] = mapped_column(String(100))
    strength_label: Mapped[str | None] = mapped_column(String(100))

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Связи
    organization = relationship("Organization", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="children")  # Для вложенности
    products = relationship("Product", back_populates="category")