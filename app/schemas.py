# Файл: app/schemas.py
# Назначение: Pydantic-схемы для валидации запросов и формирования ответов API.

from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ─── Auth ───────────────────────────────────────────────

class MagicLinkRequest(BaseModel):
    identifier: str  # email, phone или telegram username


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Organization ───────────────────────────────────────

class OrganizationBase(BaseModel):
    name: str
    slug: str
    is_active: bool = True
    settings: dict = {}


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None
    settings: dict | None = None


class OrganizationRead(OrganizationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── GlobalUser ─────────────────────────────────────────

class GlobalUserRead(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Product ────────────────────────────────────────────

class ProductBase(BaseModel):
    """Базовые поля товара."""
    name: str                              # "Elfbar 5000"
    category_id: int                       # ID категории
    supplier_id: int | None = None         # ID поставщика (опционально)
    description: str | None = None         # описание для карточки товара
    strength: str | None = None            # крепость (если применимо)
    photo_path: str | None = None          # путь к основному фото
    priority: int = 100                    # сортировка (меньше = выше)
    is_active: bool = True
    extra_data: dict = {}                  # произвольные атрибуты (JSONB)


class ProductCreate(ProductBase):
    """Схема создания товара."""
    pass


class ProductUpdate(BaseModel):
    """Обновление товара (PATCH) — все поля опциональны."""
    name: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    description: str | None = None
    strength: str | None = None
    photo_path: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    extra_data: dict | None = None


class ProductRead(ProductBase):
    """Схема ответа товара (без вариантов)."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── ProductVariant ─────────────────────────────────────

class ProductVariantBase(BaseModel):
    """Базовые поля варианта товара."""
    variant_key: str                       # машинный ключ: "strawberry", "50mg"
    name: str                              # отображаемое: "Клубника", "50мг"
    price: float                           # цена продажи
    purchase_price: float | None = None    # закупочная цена (для финансов)
    sku: str | None = None                 # артикул
    barcode: str | None = None             # штрихкод
    weight_g: int | None = None            # вес в граммах
    is_active: bool = True


class ProductVariantCreate(ProductVariantBase):
    """Схема создания варианта."""
    pass


class ProductVariantUpdate(BaseModel):
    """Обновление варианта (PATCH)."""
    variant_key: str | None = None
    name: str | None = None
    price: float | None = None
    purchase_price: float | None = None
    sku: str | None = None
    barcode: str | None = None
    weight_g: int | None = None
    is_active: bool | None = None


class ProductVariantRead(ProductVariantBase):
    """Схема ответа варианта."""
    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Product с вариантами ───────────────────────────────

class ProductWithVariantsRead(ProductRead):
    """
    Товар со списком вариантов.

    Используется при запросе конкретного товара —
    отдаём сразу все его варианты, чтобы фронтенд
    не делал дополнительный запрос.
    """
    variants: list[ProductVariantRead] = []


# ─── Category ───────────────────────────────────────────

class CategoryBase(BaseModel):
    """Базовые поля категории."""
    name: str                              # "Жидкости", "Устройства"
    slug: str | None = None                # "liquids" — для deeplink в боте
    emoji: str | None = None               # "💨" — отображается в боте
    description: str | None = None
    photo_path: str | None = None
    parent_id: int | None = None           # ID родительской категории (вложенность)
    priority: int = 100                    # сортировка: меньше = выше
    variant_label: str | None = None       # "Выберите вкус"
    strength_label: str | None = None      # "Выберите крепость"
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Схема создания категории."""
    pass


class CategoryUpdate(BaseModel):
    """Обновление категории (PATCH) — все поля опциональны."""
    name: str | None = None
    slug: str | None = None
    emoji: str | None = None
    description: str | None = None
    photo_path: str | None = None
    parent_id: int | None = None
    priority: int | None = None
    variant_label: str | None = None
    strength_label: str | None = None
    is_active: bool | None = None


class CategoryRead(CategoryBase):
    """Схема ответа категории."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeRead(CategoryRead):
    """
    Категория с вложенными подкатегориями.

    Используется для построения дерева категорий в админке и боте.
    Пример:
      {
        "id": 1, "name": "Жидкости", "children": [
          {"id": 2, "name": "Солевые", "children": []},
          {"id": 3, "name": "Классические", "children": []},
        ]
      }
    """
    children: list["CategoryTreeRead"] = []


# ─── Pagination ─────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Обёртка для пагинированных ответов."""
    items: list
    total: int
    page: int
    per_page: int


# ─── WorkerRole ─────────────────────────────────────────

class WorkerRoleBase(BaseModel):
    """Базовые поля роли сотрудника."""
    name: str                    # "Администратор", "Менеджер", "Кладовщик"
    description: str | None = None
    permissions: dict = {}       # {"can_edit_products": true, ...}


class WorkerRoleCreate(WorkerRoleBase):
    """Схема для создания роли. Поля те же что в Base."""
    pass


class WorkerRoleUpdate(BaseModel):
    """
    Схема для обновления роли (PATCH).
    Все поля опциональны — обновляем только то что передали.
    """
    name: str | None = None
    description: str | None = None
    permissions: dict | None = None


class WorkerRoleRead(WorkerRoleBase):
    """Схема ответа — включает id, org_id и временные метки."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime

    # from_attributes=True позволяет создавать схему из ORM-объекта:
    #   WorkerRoleRead.model_validate(db_role)
    model_config = ConfigDict(from_attributes=True)


# ─── Worker ─────────────────────────────────────────────

class WorkerBase(BaseModel):
    """Базовые поля сотрудника."""
    full_name: str                         # ФИО
    telegram_id: int | None = None         # Telegram ID для уведомлений
    telegram_username: str | None = None
    phone: str | None = None
    email: str | None = None
    role_id: int | None = None             # ID роли (может быть не назначена)


class WorkerCreate(WorkerBase):
    """Схема создания сотрудника."""
    pass


class WorkerUpdate(BaseModel):
    """
    Схема обновления сотрудника (PATCH).
    Все поля опциональны.
    """
    full_name: str | None = None
    telegram_id: int | None = None
    telegram_username: str | None = None
    phone: str | None = None
    email: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class WorkerRead(WorkerBase):
    """Схема ответа — включает id, org_id, статус и вложенную роль."""
    id: int
    org_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Вложенная роль — если назначена, вернётся объект WorkerRoleRead
    # Если роли нет — будет None
    role: WorkerRoleRead | None = None

    model_config = ConfigDict(from_attributes=True)

# ─── Point (точка продаж) ───────────────────────────────

class PointBase(BaseModel):
    """Базовые поля точки продаж."""
    name: str                              # "Центральный магазин"
    description: str | None = None
    address: str | None = None             # "ул. Ленина, 15"
    latitude: float | None = None          # координаты для карты
    longitude: float | None = None
    phone: str | None = None
    work_hours: dict = {}                  # {"mon": "09:00-21:00", ...}
    is_active: bool = True


class PointCreate(PointBase):
    """Схема создания точки."""
    pass


class PointUpdate(BaseModel):
    """Обновление точки (PATCH)."""
    name: str | None = None
    description: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    work_hours: dict | None = None
    is_active: bool | None = None


class PointRead(PointBase):
    """Схема ответа точки."""
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Stock (остатки) ────────────────────────────────────

class StockBase(BaseModel):
    """Базовые поля остатка."""
    product_variant_id: int                # какой вариант товара
    point_id: int                          # на какой точке
    quantity: int = 0                      # сколько есть
    min_quantity: int = 0                  # порог для уведомления "мало на складе"


class StockCreate(StockBase):
    """Схема создания записи остатка."""
    pass


class StockUpdate(BaseModel):
    """
    Обновление остатка (PATCH).
    quantity и min_quantity — единственное что имеет смысл менять вручную.
    reserved_quantity меняется автоматически (корзина / заказ).
    """
    quantity: int | None = None
    min_quantity: int | None = None


class StockRead(StockBase):
    """Схема ответа остатка."""
    id: int
    reserved_quantity: int                 # зарезервировано в корзинах
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    """
    Корректировка остатка — прибавить или убавить количество.

    Используется когда нужно:
      - принять поставку (+50)
      - списать бракованный товар (-3)
      - провести инвентаризацию (установить точное значение)

    delta: изменение количества (положительное — приход, отрицательное — расход)
    reason: причина корректировки (записывается в inventory_moves)
    """
    delta: int                             # +50 или -3
    reason: str | None = None              # "Поставка от 12.03" или "Списание брака"


# ─── InventoryMove (история движений) ──────────────────

class InventoryMoveRead(BaseModel):
    """Схема ответа движения товара."""
    id: int
    org_id: int
    product_variant_id: int
    from_point_id: int | None = None
    to_point_id: int | None = None
    move_type: str                         # "purchase", "sale", "adjustment" и т.д.
    quantity: int
    reference_id: int | None = None        # ID связанного объекта (заказ, закупка)
    reference_type: str | None = None      # "order", "purchase"
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ─── CartItem (корзина) ─────────────────────────────────

class CartItemAdd(BaseModel):
    """
    Добавление товара в корзину.
    Покупатель выбирает вариант и количество.
    Точка берётся из его текущей сессии (user_point_session).
    """
    product_variant_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    """Изменение количества товара в корзине."""
    quantity: int


class CartItemRead(BaseModel):
    """Элемент корзины в ответе."""
    id: int
    product_variant_id: int
    point_id: int
    quantity: int
    price_snapshot: float | None = None    # цена на момент добавления
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── UserAddress (адреса доставки) ──────────────────────

class UserAddressBase(BaseModel):
    """Базовые поля адреса."""
    label: str | None = None               # "Дом", "Работа"
    address: str                           # полный текстовый адрес
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False


class UserAddressCreate(UserAddressBase):
    pass


class UserAddressRead(UserAddressBase):
    id: int
    org_user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Order (заказы) ─────────────────────────────────────

class OrderItemRead(BaseModel):
    """Позиция в заказе."""
    id: int
    product_variant_id: int
    quantity: int
    price: float                           # цена на момент заказа
    purchase_price: float | None = None
    discount_amount: float = 0
    line_total: float | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    """Заказ в ответе."""
    id: int
    order_id: str                          # публичный номер "ORD-A1B2C3D4"
    org_id: int
    org_user_id: int
    point_id: int
    status: str
    delivery: str
    delivery_address_raw: str | None = None
    delivery_fee: float
    comment: str | None = None
    admin_comment: str | None = None
    items_total: float
    discount_type: str | None = None
    discount_amount: float | None = None
    total_price: float
    payment_status: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """
    Оформление заказа из корзины.
    Покупатель выбирает тип доставки и опционально адрес.
    """
    delivery: str = "pickup"               # "pickup" или "delivery"
    delivery_address_id: int | None = None # ID сохранённого адреса
    delivery_address_raw: str | None = None # или текст адреса вручную
    comment: str | None = None             # комментарий к заказу


class OrderStatusChange(BaseModel):
    """Смена статуса заказа сотрудником."""
    new_status: str                        # "confirmed", "processing", "ready" и т.д.
    comment: str | None = None             # причина / комментарий


class OrderStatusHistoryRead(BaseModel):
    """Запись из истории статусов."""
    id: int
    old_status: str | None = None
    new_status: str
    changed_by: int | None = None
    comment: str | None = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── LoyaltyProgram (программа лояльности) ──────────────

class LoyaltyProgramBase(BaseModel):
    """Настройки программы лояльности организации."""
    name: str                              # "Основная программа"
    accrual_percent: float = 2.0           # % начисления от суммы заказа
    min_order_for_accrual: float = 0       # мин. сумма заказа для начисления
    max_discount_percent: float = 100      # макс. % скидки при оплате баллами
    min_points_for_redemption: float = 1   # мин. баллов для списания
    points_expire_days: int | None = None  # через сколько дней баллы сгорают (None = никогда)
    is_active: bool = True


class LoyaltyProgramCreate(LoyaltyProgramBase):
    pass


class LoyaltyProgramUpdate(BaseModel):
    name: str | None = None
    accrual_percent: float | None = None
    min_order_for_accrual: float | None = None
    max_discount_percent: float | None = None
    min_points_for_redemption: float | None = None
    points_expire_days: int | None = None
    is_active: bool | None = None


class LoyaltyProgramRead(LoyaltyProgramBase):
    id: int
    org_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── LoyaltyTier (уровни клиентов) ─────────────────────

class LoyaltyTierBase(BaseModel):
    """Уровень лояльности: бронза, серебро, золото и т.д."""
    name: str                              # "Бронза", "Серебро", "Золото"
    min_orders_amount: float = 0           # мин. сумма покупок для достижения уровня
    accrual_multiplier: float = 1.0        # множитель начисления (1.5 = x1.5 баллов)
    discount_percent: float = 0            # автоматическая скидка на заказ
    color_hex: str | None = "#94a3b8"      # цвет для отображения в интерфейсе
    icon_emoji: str | None = None          # эмодзи уровня
    priority: int = 100                    # сортировка (меньше = выше)


class LoyaltyTierCreate(LoyaltyTierBase):
    pass


class LoyaltyTierUpdate(BaseModel):
    name: str | None = None
    min_orders_amount: float | None = None
    accrual_multiplier: float | None = None
    discount_percent: float | None = None
    color_hex: str | None = None
    icon_emoji: str | None = None
    priority: int | None = None


class LoyaltyTierRead(LoyaltyTierBase):
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── LoyaltyTransaction (движения баллов) ───────────────

class LoyaltyTransactionRead(BaseModel):
    """Запись о начислении/списании баллов."""
    id: int
    org_user_id: int
    order_id: int | None = None
    points: float                          # положительное — начисление, отрицательное — списание
    available_points: float
    type: str                              # "order_accrual", "redemption" и т.д.
    description: str | None = None
    expires_at: datetime | None = None
    is_expired: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualPointsAdjustment(BaseModel):
    """Ручное начисление/списание баллов администратором."""
    org_user_id: int                       # кому
    points: float                          # +100 или -50
    description: str | None = None         # "Бонус за отзыв"


# ─── Promotion (акции и промокоды) ──────────────────────

class PromotionBase(BaseModel):
    """Настройки акции."""
    name: str                              # "Скидка 10% на всё"
    promo_code: str | None = None          # "SALE10" (None = автоматическая акция)
    promo_type: str = "percent"            # "percent", "fixed_rub", "free_shipping", "gift_product"
    value: float                           # 10 (процент) или 500 (рублей)
    min_order: float = 0                   # мин. сумма заказа для применения
    max_discount: float | None = None      # макс. сумма скидки
    max_uses: int | None = None            # лимит использований (None = без лимита)
    per_user_limit: int = 1                # сколько раз один покупатель может использовать
    applies_to: dict = {}                  # {"all": true} или {"categories": [1,2]}
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True


class PromotionCreate(PromotionBase):
    pass


class PromotionUpdate(BaseModel):
    name: str | None = None
    promo_code: str | None = None
    promo_type: str | None = None
    value: float | None = None
    min_order: float | None = None
    max_discount: float | None = None
    max_uses: int | None = None
    per_user_limit: int | None = None
    applies_to: dict | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None


class PromotionRead(PromotionBase):
    id: int
    org_id: int
    uses_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── ReferralCode (реферальные коды) ────────────────────

class ReferralCodeRead(BaseModel):
    id: int
    org_user_id: int
    code: str
    uses_count: int
    max_uses: int | None = None
    bonus_points: float
    new_user_bonus: float
    is_active: bool
    expires_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── NotificationTemplate (шаблоны уведомлений) ────────

class NotificationTemplateBase(BaseModel):
    """Шаблон уведомления. Поддерживает переменные в фигурных скобках."""
    type: str                              # "order_created", "order_confirmed" и т.д.
    name: str                              # "Новый заказ"
    body: str                              # "Заказ {order_id} на сумму {total} создан!"
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: str | None = None
    body: str | None = None
    is_active: bool | None = None


class NotificationTemplateRead(NotificationTemplateBase):
    id: int
    org_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── NotificationQueue (очередь уведомлений) ───────────

class NotificationQueueRead(BaseModel):
    """Запись из очереди уведомлений."""
    id: int
    org_id: int
    org_user_id: int
    template_id: int | None = None
    type: str
    payload: dict = {}
    scheduled_at: datetime
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    error: str | None = None
    attempts: int

    model_config = ConfigDict(from_attributes=True)


class NotificationSend(BaseModel):
    """Ручная отправка уведомления (из админки)."""
    org_user_id: int                       # кому
    type: str                              # тип шаблона
    payload: dict = {}                     # переменные: {"order_id": "ORD-123", "total": 1500}


# ─── AuditLog (журнал аудита) ──────────────────────────

class AuditLogRead(BaseModel):
    """Запись аудита."""
    id: int
    org_id: int | None = None
    actor_id: int | None = None
    actor_type: str
    action: str                            # "create", "update", "delete" и т.д.
    entity_type: str                       # "product", "order", "worker" и т.д.
    entity_id: str | None = None
    old_data: dict | None = None
    new_data: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Supplier (поставщики) ──────────────────────────────

class SupplierBase(BaseModel):
    name: str
    contact: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class SupplierRead(SupplierBase):
    id: int
    org_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Expense (расходы) ──────────────────────────────────

class ExpenseBase(BaseModel):
    expense_date: str | None = None        # "2025-03-12" (ISO формат)
    amount: float
    category: str                          # "salary", "purchase", "rent" и т.д.
    description: str | None = None
    point_id: int | None = None            # к какой точке относится расход


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: float | None = None
    category: str | None = None
    description: str | None = None
    point_id: int | None = None


class ExpenseRead(BaseModel):
    id: int
    org_id: int
    expense_date: str                      # дата в виде строки
    amount: float
    category: str
    description: str | None = None
    point_id: int | None = None
    worker_payment_id: int | None = None
    purchase_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── WorkerPayment (выплаты сотрудникам) ────────────────

class WorkerPaymentBase(BaseModel):
    worker_id: int
    amount: float
    payment_date: str | None = None        # "2025-03-12"
    period_start: str | None = None
    period_end: str | None = None
    description: str | None = None


class WorkerPaymentCreate(WorkerPaymentBase):
    pass


class WorkerPaymentRead(BaseModel):
    id: int
    worker_id: int
    amount: float
    payment_date: str
    period_start: str | None = None
    period_end: str | None = None
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Purchase (закупки) ─────────────────────────────────

class PurchaseItemCreate(BaseModel):
    """Позиция в закупке."""
    product_variant_id: int
    point_id: int                          # на какую точку поступает товар
    quantity: int
    price: float                           # закупочная цена за единицу


class PurchaseItemRead(BaseModel):
    id: int
    product_variant_id: int
    point_id: int
    quantity: int
    price: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseCreate(BaseModel):
    """Создание закупки с позициями."""
    supplier_id: int | None = None
    purchase_date: str | None = None       # "2025-03-12"
    description: str | None = None
    items: list[PurchaseItemCreate]        # минимум одна позиция


class PurchaseRead(BaseModel):
    id: int
    org_id: int
    supplier_id: int | None = None
    amount: float
    purchase_date: str
    description: str | None = None
    created_at: datetime
    items: list[PurchaseItemRead] = []

    model_config = ConfigDict(from_attributes=True)


# ─── Report (отчёты) ────────────────────────────────────

class ReportRead(BaseModel):
    id: int
    org_id: int
    report_type: str                       # "daily", "weekly", "monthly"
    period_start: str
    period_end: str
    point_id: int | None = None
    revenue: float
    expenses_total: float
    orders_count: int
    new_users: int
    details: dict = {}
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportGenerate(BaseModel):
    """Запрос на генерацию отчёта."""
    report_type: str = "daily"             # "daily", "weekly", "monthly"
    period_start: str                      # "2025-03-01"
    period_end: str                        # "2025-03-31"
    point_id: int | None = None            # None = по всей организации


# ─── DeliveryZone (зоны доставки) ───────────────────────

class DeliveryZoneBase(BaseModel):
    name: str                              # "Центр", "Северный район"
    min_order: float = 0                   # мин. сумма заказа для доставки
    delivery_fee: float = 0                # стоимость доставки
    free_from: float | None = None         # сумма, с которой доставка бесплатна
    est_minutes: int | None = None         # примерное время доставки
    is_active: bool = True


class DeliveryZoneCreate(DeliveryZoneBase):
    pass


class DeliveryZoneUpdate(BaseModel):
    name: str | None = None
    min_order: float | None = None
    delivery_fee: float | None = None
    free_from: float | None = None
    est_minutes: int | None = None
    is_active: bool | None = None


class DeliveryZoneRead(DeliveryZoneBase):
    id: int
    point_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── PointWorker (привязка сотрудников к точкам) ────────

class PointWorkerCreate(BaseModel):
    worker_id: int
    is_primary: bool = False               # основной менеджер точки


class PointWorkerRead(BaseModel):
    id: int
    point_id: int
    worker_id: int
    is_primary: bool
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── UserAddress (адреса покупателей) — уже есть выше ───
# ─── UserPointSession (выбранная точка) ─────────────────

class UserPointSessionRead(BaseModel):
    org_user_id: int
    point_id: int
    selected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPointSessionSet(BaseModel):
    point_id: int


# ─── PaymentMethod (способы оплаты) ────────────────────

class PaymentMethodBase(BaseModel):
    name: str                              # "Наличные", "Перевод на карту"
    code: str                              # "cash", "card_transfer"
    is_active: bool = True


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodRead(PaymentMethodBase):
    id: int
    org_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── ProductTag (теги товаров) ──────────────────────────

class ProductTagBase(BaseModel):
    name: str                              # "Новинка", "Хит продаж", "Акция"
    color_hex: str | None = None           # "#ff6b6b"


class ProductTagCreate(ProductTagBase):
    pass


class ProductTagRead(ProductTagBase):
    id: int
    org_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── CashRegister (кассы) ──────────────────────────────

class CashRegisterBase(BaseModel):
    name: str = "Основная касса"
    balance: float = 0


class CashRegisterCreate(CashRegisterBase):
    point_id: int


class CashRegisterRead(CashRegisterBase):
    id: int
    point_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CashRegisterAdjust(BaseModel):
    amount: float                          # +5000 (внесение) или -2000 (изъятие)
    reason: str | None = None


# ─── ReferralCode (реферальные коды) — Read уже есть ────
# ─── Faq ────────────────────────────────────────────────

class FaqBase(BaseModel):
    question: str
    answer: str
    priority: int = 100
    is_active: bool = True


class FaqCreate(FaqBase):
    pass


class FaqUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    priority: int | None = None
    is_active: bool | None = None


class FaqRead(FaqBase):
    id: int
    org_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── Link (полезные ссылки) ─────────────────────────────

class LinkBase(BaseModel):
    title: str
    url: str
    priority: int = 100
    is_active: bool = True


class LinkCreate(LinkBase):
    pass


class LinkRead(LinkBase):
    id: int
    org_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── Delivery (доставка и геокодирование) ───────────────

class DeliveryCalcRequest(BaseModel):
    """Запрос расчёта стоимости доставки."""
    point_id: int
    zone_id: int | None = None             # None = самовывоз
    order_total: float


class DeliveryCalcResponse(BaseModel):
    """Результат расчёта доставки."""
    delivery_fee: float
    zone_name: str | None = None
    est_minutes: int | None = None
    is_free: bool
    min_order_met: bool


class AddressResolveRequest(BaseModel):
    """Запрос на определение адреса."""
    address_text: str | None = None        # текст: "Москва Ленина 2"
    latitude: float | None = None          # или координаты
    longitude: float | None = None


class AddressResolveResponse(BaseModel):
    """Нормализованный адрес."""
    formatted_address: str                 # полный адрес от Nominatim
    short_address: str                     # "д. 2, ул. Ленина, г. Москва"
    latitude: float
    longitude: float


# ─── ProductMedia (фото/видео товаров) ──────────────────

class ProductMediaCreate(BaseModel):
    media_type: str = "photo"              # "photo" или "video"
    path: str                              # путь к файлу на сервере
    telegram_file_id: str | None = None    # кеш Telegram file_id
    position: int = 0                      # порядок отображения


class ProductMediaRead(BaseModel):
    id: int
    product_id: int
    media_type: str
    path: str
    telegram_file_id: str | None = None
    position: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── PriceList (прайс-листы) ───────────────────────────

class PriceListBase(BaseModel):
    name: str                              # "Розничный", "Оптовый"
    is_default: bool = False
    is_active: bool = True


class PriceListCreate(PriceListBase):
    pass


class PriceListRead(PriceListBase):
    id: int
    org_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceListItemCreate(BaseModel):
    product_variant_id: int
    price: float
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PriceListItemRead(BaseModel):
    id: int
    price_list_id: int
    product_variant_id: int
    price: float
    valid_from: datetime
    valid_until: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ─── Broadcast (массовая рассылка) ─────────────────────

class BroadcastRequest(BaseModel):
    """Запрос на массовую рассылку."""
    message: str                           # текст сообщения
    tier_id: int | None = None             # фильтр по уровню лояльности (None = все)
    is_active_only: bool = True            # только активным пользователям