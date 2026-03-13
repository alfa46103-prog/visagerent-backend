# Файл: app/models/product.py
# Назначение: Модели для товаров (products) и их вариантов (product_variants).
# Товар имеет общие характеристики (название, описание, фото), а варианты —
# конкретные исполнения (например, разные вкусы, веса) с ценой, артикулом и т.д.

from datetime import datetime
from sqlalchemy import String, Boolean, Text, SmallInteger, JSON, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import sqlalchemy as sa

from app.core.database import Base      # Base теперь берётся отсюда
from app.models.base import TimestampMixin


class Product(Base, TimestampMixin):
    """
    Товар (общая карточка). Может иметь несколько вариантов (например, разные вкусы).
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"))

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Название товара
    description: Mapped[str | None] = mapped_column(Text)
    strength: Mapped[str | None] = mapped_column(String(50))        # Крепость (для специфики)
    photo_path: Mapped[str | None] = mapped_column(String(255))     # Основное фото
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)  # Для сортировки
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=False, default={})  # Произвольные атрибуты
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Связи
    organization = relationship("Organization", back_populates="products")
    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    supplier = relationship("Supplier", back_populates="products") 
    media = relationship("ProductMedia", back_populates="product", cascade="all, delete-orphan")
    tags = relationship("ProductTag", secondary="product_tag_links", back_populates="products")


class ProductVariant(Base, TimestampMixin):
    """
    Вариант товара (например, конкретный вкус или вес).
    Содержит цену, артикул, штрихкод и т.д.
    """
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    variant_key: Mapped[str] = mapped_column(String(100), nullable=False)  # Уникальный ключ внутри товара (например, "strawberry")
    name: Mapped[str] = mapped_column(String(255), nullable=False)         # Отображаемое название варианта
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # Цена
    purchase_price: Mapped[float | None] = mapped_column(Numeric(10, 2))  # Закупочная цена (для финансов)
    sku: Mapped[str | None] = mapped_column(String(100), index=True)      # Артикул
    barcode: Mapped[str | None] = mapped_column(String(50))               # Штрихкод
    weight_g: Mapped[int | None] = mapped_column(SmallInteger)            # Вес в граммах
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Связи
    product = relationship("Product", back_populates="variants")

    # Уникальность ключа в пределах товара
    __table_args__ = (
        sa.UniqueConstraint("product_id", "variant_key", name="uq_product_variant_key"),
    )