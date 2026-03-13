# Файл: app/models/order.py
# Назначение: Основная модель заказа.
# Содержит всю информацию о заказе: статус, тип доставки, суммы, скидки, комментарии.
# Использует ENUM-типы, которые мы создали в БД.

from sqlalchemy import String, Integer, Numeric, ForeignKey, Text, Enum, CheckConstraint, UniqueConstraint, Text, BigInteger
from sqlalchemy.sql import text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class OrderStatus(str, enum.Enum):
    """Статусы заказа (соответствуют ENUM в БД)."""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class DeliveryType(str, enum.Enum):
    """Типы доставки."""
    PICKUP = "pickup"
    DELIVERY = "delivery"
    EXPRESS = "express"


class PaymentStatus(str, enum.Enum):
    """Статусы оплаты."""
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    FAILED = "failed"


class DiscountType(str, enum.Enum):
    """Типы скидок."""
    LOYALTY_POINTS = "loyalty_points"
    PERCENT = "percent"
    RUB = "rub"
    SET_PRICE = "set_price"
    PROMO_CODE = "promo_code"
    TIER_DISCOUNT = "tier_discount"

import uuid


def generate_order_id() -> str:
    """Генерирует публичный номер заказа: ORD-A1B2C3D4"""
    return "ORD-" + uuid.uuid4().hex[:8].upper()


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(
            String(50),
            nullable=False,
            unique=True,
            default=generate_order_id,
        )
    """Публичный номер заказа (генерируется автоматически)."""

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    org_user_id: Mapped[int] = mapped_column(
        ForeignKey("organization_users.id", ondelete="RESTRICT"),
        nullable=False
    )
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.id", ondelete="RESTRICT"),
        nullable=False
    )
    price_list_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_lists.id", ondelete="SET NULL")
    )
    promotion_id: Mapped[int | None] = mapped_column(
        ForeignKey("promotions.id", ondelete="SET NULL")
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", create_type=False),
        nullable=False,
        default=OrderStatus.PENDING
    )
    delivery: Mapped[DeliveryType] = mapped_column(
        Enum(DeliveryType, name="delivery_type", create_type=False),
        nullable=False,
        default=DeliveryType.PICKUP
    )
    delivery_zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_zones.id", ondelete="SET NULL")
    )
    delivery_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_addresses.id", ondelete="SET NULL")
    )
    delivery_address_raw: Mapped[str | None] = mapped_column(Text)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    comment: Mapped[str | None] = mapped_column(Text)
    admin_comment: Mapped[str | None] = mapped_column(Text)

    items_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_type: Mapped[DiscountType | None] = mapped_column(
        Enum(DiscountType, name="discount_type", create_type=False)
    )
    discount_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    purchasing_price: Mapped[float | None] = mapped_column(Numeric(10, 2))

    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", create_type=False),
        nullable=False,
        default=PaymentStatus.PENDING
    )
    chat_message_id: Mapped[int | None] = mapped_column(BigInteger)

    # Вычисляемое поле маржи (генерируется базой)
    margin: Mapped[float | None] = mapped_column(Numeric(10, 2), server_default=text("0"))

    # Связи
    organization = relationship("Organization")
    user = relationship("OrganizationUser", backref="orders")
    point = relationship("Point", backref="orders")
    price_list = relationship("PriceList")
    promotion = relationship("Promotion")
    delivery_zone = relationship("DeliveryZone")
    address = relationship("UserAddress")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")