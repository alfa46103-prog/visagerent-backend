# Файл: app/models/product_media.py
# Назначение: Фотографии и видео товаров.
# Позволяет хранить несколько медиафайлов для одного товара.
# Telegram file_id кешируется для быстрой отправки в боте.

from sqlalchemy import String, Integer, SmallInteger, ForeignKey, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.core.database import Base


class MediaType(str, enum.Enum):
    """Тип медиафайла."""
    PHOTO = "photo"
    VIDEO = "video"


class ProductMedia(Base):
    __tablename__ = "product_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type", create_type=False),
        nullable=False,
        default=MediaType.PHOTO
    )
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    """Путь к файлу на сервере."""

    telegram_file_id: Mapped[str | None] = mapped_column(String(512))
    """ID файла в Telegram (для кеширования)."""

    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    """Порядок отображения (меньше = выше)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    product = relationship("Product", back_populates="media")