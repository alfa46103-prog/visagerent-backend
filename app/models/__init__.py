# Файл: app/models/__init__.py
# Назначение: Импорт всех моделей SQLAlchemy для регистрации в Base.metadata.
# Этот файл позволяет Alembic обнаружить все модели при генерации миграций.
# Также предоставляет удобный список __all__ для импорта в других частях приложения.

from app.core.database import Base

# Импортируем модели в алфавитном порядке для удобства
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.delivery_zone import DeliveryZone
from app.models.global_user import GlobalUser
from app.models.inventory_move import InventoryMove
from app.models.loyalty_tier import LoyaltyTier
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_payment import OrderPayment
from app.models.order_status_history import OrderStatusHistory
from app.models.organization import Organization
from app.models.organization_user import OrganizationUser
from app.models.payment_method import PaymentMethod
from app.models.point import Point
from app.models.point_worker import PointWorker
from app.models.price_list import PriceList
from app.models.price_list_item import PriceListItem
from app.models.product import Product, ProductVariant
from app.models.promotion import Promotion
from app.models.promotion_use import PromotionUse
from app.models.stock import Stock
from app.models.stock_reservation import StockReservation
from app.models.supplier import Supplier
from app.models.user_address import UserAddress
from app.models.user_point_session import UserPointSession
from app.models.worker import Worker
from app.models.worker_role import WorkerRole
from app.models.product_tag import ProductTag
from app.models.product_media import ProductMedia
from app.models.product_tag_link import ProductTagLink
from app.models.referral_code import ReferralCode
from app.models.cash_register import CashRegister
from app.models.loyalty_program import LoyaltyProgram
from app.models.loyalty_transaction import LoyaltyTransaction
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.worker_payment import WorkerPayment
from app.models.expense import Expense
from app.models.audit_log import AuditLog
from app.models.bot_session import BotSession
from app.models.report import Report
from app.models.notification_template import NotificationTemplate
from app.models.notification_queue import NotificationQueue
from app.models.link import Link
from app.models.faq import Faq
from app.models.magic_token import MagicToken

# Вспомогательный миксин (не модель, но может пригодиться)
from app.models.base import TimestampMixin

# Список всех объектов, доступных для импорта из этого пакета
__all__ = [
    "Base",
    "TimestampMixin",
    "CartItem",
    "Category",
    "DeliveryZone",
    "GlobalUser",
    "InventoryMove",
    "LoyaltyTier",
    "Order",
    "OrderItem",
    "OrderPayment",
    "OrderStatusHistory",
    "Organization",
    "OrganizationUser",
    "PaymentMethod",
    "Point",
    "PointWorker",
    "PriceList",
    "PriceListItem",
    "Product",
    "ProductVariant",
    "Promotion",
    "PromotionUse",
    "Stock",
    "StockReservation",
    "Supplier",
    "UserAddress",
    "UserPointSession",
    "Worker",
    "WorkerRole",
    "AuditLog",
    "BotSession",
    "CashRegister",
    "Expense",
    "Link",
    "LoyaltyProgram",
    "LoyaltyTransaction",
    "NotificationQueue",
    "NotificationTemplate",
    "ProductMedia",
    "ProductTag",
    "ProductTagLink",
    "Purchase",
    "PurchaseItem",
    "ReferralCode",
    "Report",
    "WorkerPayment",
    "Faq",
    "MagicToken",
]