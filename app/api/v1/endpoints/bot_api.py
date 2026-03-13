# Файл: app/api/v1/endpoints/bot_api.py
# Назначение: Специальные эндпоинты для Telegram-бота.
#
# Бот авторизуется сервисным токеном (type="service").
# Покупатель идентифицируется по telegram_id в параметрах запроса.
#
# Эти эндпоинты — прослойка между ботом и основными сервисами.
# Они принимают telegram_id, находят нужного пользователя,
# и вызывают сервисы от его имени.

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.dependencies import get_service_org_id
from app.models.global_user import GlobalUser
from app.models.organization_user import OrganizationUser
from app.models.worker import Worker
from app.models.worker_role import WorkerRole
from app.models.order import Order
from app.services import cart as cart_service
from app.services import order as order_service
from app.services import loyalty as loyalty_service
from app.services import extras

router = APIRouter()


# ── Вспомогательные функции ────────────────────────────

async def _get_or_create_org_user(
    db: AsyncSession,
    telegram_id: int,
    org_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> OrganizationUser:
    """
    Найти или создать пользователя в организации.

    GlobalUser создаётся по telegram_id.
    OrganizationUser — связь между GlobalUser и организацией.
    """
    # Ищем или создаём GlobalUser
    stmt = select(GlobalUser).where(GlobalUser.id == telegram_id)
    result = await db.execute(stmt)
    global_user = result.scalar_one_or_none()

    if not global_user:
        global_user = GlobalUser(
            id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(global_user)
        await db.commit()
        await db.refresh(global_user)

    # Ищем или создаём OrganizationUser
    ou_stmt = select(OrganizationUser).where(
        OrganizationUser.user_id == telegram_id,
        OrganizationUser.org_id == org_id,
    )
    ou_result = await db.execute(ou_stmt)
    org_user = ou_result.scalar_one_or_none()

    if not org_user:
        org_user = OrganizationUser(
            org_id=org_id,
            user_id=telegram_id,
        )
        db.add(org_user)
        await db.commit()
        await db.refresh(org_user)

    return org_user


async def _get_org_user(
    db: AsyncSession,
    telegram_id: int,
    org_id: int,
) -> OrganizationUser | None:
    """Найти OrganizationUser по telegram_id (без создания)."""
    stmt = select(OrganizationUser).where(
        OrganizationUser.user_id == telegram_id,
        OrganizationUser.org_id == org_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Регистрация ───────────────────────────────────────

class RegisterUserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    referral_code: str | None = None


@router.post("/register-user")
async def register_user(
    data: RegisterUserRequest,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Регистрация покупателя при /start."""
    org_user = await _get_or_create_org_user(
        db, data.telegram_id, org_id,
        data.username, data.first_name, data.last_name,
    )

    # Обработка реферального кода
    if data.referral_code and not org_user.referrer_id:
        from app.models.referral_code import ReferralCode
        ref_stmt = select(ReferralCode).where(
            ReferralCode.code == data.referral_code,
            ReferralCode.is_active == True,
        )
        ref_result = await db.execute(ref_stmt)
        ref_code = ref_result.scalar_one_or_none()

        if ref_code and ref_code.org_user_id != org_user.id:
            org_user.referrer_id = ref_code.org_user_id
            await db.commit()

    return {"ok": True, "org_user_id": org_user.id}


# ── Профиль ───────────────────────────────────────────

@router.get("/profile")
async def get_profile(
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Профиль покупателя для бота."""
    org_user = await _get_org_user(db, telegram_id, org_id)
    if not org_user:
        return {"error": True, "detail": "User not found"}

    # Баланс баллов
    balance = await loyalty_service.get_user_balance(db, org_user.id, org_id)

    # Уровень
    tier_name = "Без уровня"
    if org_user.tier_id:
        from app.models.loyalty_tier import LoyaltyTier
        tier = await db.get(LoyaltyTier, org_user.tier_id)
        if tier:
            tier_name = tier.name

    # Количество заказов
    orders_stmt = select(Order).where(
        Order.org_user_id == org_user.id,
        Order.org_id == org_id,
    )
    orders_result = await db.execute(orders_stmt)
    orders_count = len(list(orders_result.scalars().all()))

    # Реферальный код
    ref_code = await extras.get_or_create_referral_code(db, org_user.id)

    # GlobalUser для имени
    global_user = await db.get(GlobalUser, telegram_id)

    return {
        "first_name": global_user.first_name if global_user else "",
        "balance": balance,
        "tier_name": tier_name,
        "orders_count": orders_count,
        "total_spent": float(org_user.total_orders_amount),
        "referral_code": ref_code.code if ref_code else "",
    }


# ── Точки ─────────────────────────────────────────────

@router.get("/points")
async def get_points(
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Список активных точек организации."""
    from app.services import point as point_service
    points = await point_service.get_points(db, org_id, is_active=True)
    return [{"id": p.id, "name": p.name, "address": p.address} for p in points]


class SelectPointRequest(BaseModel):
    telegram_id: int
    point_id: int


@router.post("/select-point")
async def select_point(
    data: SelectPointRequest,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Выбрать точку продаж."""
    org_user = await _get_org_user(db, data.telegram_id, org_id)
    if not org_user:
        return {"error": True, "detail": "User not found"}

    await extras.set_user_point(db, org_user.id, data.point_id)
    return {"ok": True}


# ── Корзина ───────────────────────────────────────────

class AddToCartRequest(BaseModel):
    telegram_id: int
    product_variant_id: int
    quantity: int = 1


@router.post("/cart/add")
async def add_to_cart(
    data: AddToCartRequest,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Добавить товар в корзину."""
    org_user = await _get_org_user(db, data.telegram_id, org_id)
    if not org_user:
        return {"error": True, "detail": "User not found"}

    from app.schemas import CartItemAdd
    item = await cart_service.add_to_cart(
        db, org_user.id, CartItemAdd(
            product_variant_id=data.product_variant_id,
            quantity=data.quantity,
        )
    )
    return {"ok": True, "cart_item_id": item.id}


@router.get("/cart")
async def get_cart(
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Содержимое корзины."""
    org_user = await _get_org_user(db, telegram_id, org_id)
    if not org_user:
        return []

    items = await cart_service.get_cart(db, org_user.id)
    return [
        {
            "id": item.id,
            "product_variant_id": item.product_variant_id,
            "quantity": item.quantity,
            "price_snapshot": float(item.price_snapshot) if item.price_snapshot else 0,
            "variant_name": str(item.product_variant_id),  # в будущем подгружать имя
        }
        for item in items
    ]


@router.delete("/cart/clear")
async def clear_cart(
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Очистить корзину."""
    org_user = await _get_org_user(db, telegram_id, org_id)
    if not org_user:
        return {"ok": True}

    await cart_service.clear_cart(db, org_user.id)
    return {"ok": True}


# ── Заказы ────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    telegram_id: int
    delivery: str = "pickup"
    delivery_address_raw: str | None = None
    comment: str | None = None


@router.post("/orders/create")
async def create_order(
    data: CreateOrderRequest,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Создать заказ из корзины и уведомить сотрудников."""
    org_user = await _get_org_user(db, data.telegram_id, org_id)
    if not org_user:
        return {"error": True, "detail": "User not found"}

    from app.schemas import OrderCreate
    order = await order_service.create_order_from_cart(
        db, org_user.id, org_id,
        OrderCreate(
            delivery=data.delivery,
            delivery_address_raw=data.delivery_address_raw,
            comment=data.comment,
        ),
    )

    # Уведомляем сотрудников точки о новом заказе
    from app.models.point_worker import PointWorker
    pw_stmt = select(PointWorker).where(
        PointWorker.point_id == order.point_id,
        PointWorker.removed_at.is_(None),
    )
    pw_result = await db.execute(pw_stmt)
    point_workers = list(pw_result.scalars().all())

    # Для каждого сотрудника точки ставим уведомление в очередь
    from app.services.notification import enqueue_notification
    for pw in point_workers:
        worker = await db.get(Worker, pw.worker_id)
        if worker and worker.is_active:
            # Ищем OrganizationUser по worker (для notification_queue.org_user_id)
            # Используем worker.id как ссылку
            await enqueue_notification(
                db, org_id,
                org_user_id=org_user.id,  # от чьего имени заказ
                notification_type="order_created",
                payload={
                    "order_id": order.order_id,
                    "total": str(order.total_price),
                    "worker_telegram_id": str(worker.telegram_id) if worker.telegram_id else "",
                },
            )

    # Также возвращаем primary worker для кнопки "Связаться с менеджером"
    primary_worker_username = None
    for pw in point_workers:
        if pw.is_primary:
            worker = await db.get(Worker, pw.worker_id)
            if worker and worker.telegram_username:
                primary_worker_username = worker.telegram_username
                break

    return {
        "order_id": order.order_id,
        "id": order.id,
        "total_price": float(order.total_price),
        "manager_username": primary_worker_username,
    }


@router.get("/my-orders")
async def get_my_orders(
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Заказы покупателя."""
    org_user = await _get_org_user(db, telegram_id, org_id)
    if not org_user:
        return []

    orders = await order_service.get_orders(db, org_id, org_user_id=org_user.id)
    return [
        {
            "id": o.id,
            "order_id": o.order_id,
            "status": o.status.value,
            "total_price": float(o.total_price),
            "delivery": o.delivery.value,
        }
        for o in orders
    ]


# ── FAQ ───────────────────────────────────────────────

@router.get("/faq")
async def get_faq(
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """FAQ для бота."""
    faqs = await extras.get_faqs(db, org_id)
    return [{"question": f.question, "answer": f.answer} for f in faqs]


# ── Сотрудник ─────────────────────────────────────────

@router.get("/worker/me")
async def get_worker_profile(
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Профиль сотрудника по telegram_id."""
    stmt = (
        select(Worker)
        .where(Worker.telegram_id == telegram_id, Worker.org_id == org_id, Worker.is_active == True)
        .options(selectinload(Worker.role))
    )
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()

    if not worker:
        return {"error": True, "detail": "Worker not found"}

    return {
        "id": worker.id,
        "full_name": worker.full_name,
        "role_name": worker.role.name if worker.role else "Без роли",
    }


@router.get("/worker/orders")
async def get_worker_orders(
    telegram_id: int = Query(...),
    status: str | None = Query(None),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Заказы для сотрудника."""
    orders = await order_service.get_orders(db, org_id, status=status)
    return [
        {
            "id": o.id,
            "order_id": o.order_id,
            "status": o.status.value,
            "total_price": float(o.total_price),
        }
        for o in orders
    ]


@router.get("/worker/orders/{order_id}")
async def get_worker_order_detail(
    order_id: int,
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Детали заказа для сотрудника."""
    order = await order_service.get_order_by_id(db, order_id, org_id)
    return {
        "id": order.id,
        "order_id": order.order_id,
        "status": order.status.value,
        "total_price": float(order.total_price),
        "delivery": order.delivery.value,
        "delivery_address_raw": order.delivery_address_raw,
        "comment": order.comment,
        "items": [
            {
                "variant_name": str(item.product_variant_id),
                "quantity": item.quantity,
                "price": float(item.price),
            }
            for item in order.items
        ],
    }


class ChangeStatusRequest(BaseModel):
    telegram_id: int
    new_status: str


@router.post("/worker/orders/{order_id}/status")
async def change_order_status(
    order_id: int,
    data: ChangeStatusRequest,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Сменить статус заказа (от сотрудника)."""
    from app.schemas import OrderStatusChange
    order = await order_service.change_order_status(
        db, order_id, org_id,
        OrderStatusChange(new_status=data.new_status),
    )
    return {"ok": True, "status": order.status.value}


# ── Медиа товара ──────────────────────────────────────

@router.get("/product-media/{product_id}")
async def get_product_media(
    product_id: int,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Фото/видео товара для бота."""
    from app.models.product_media import ProductMedia
    stmt = (
        select(ProductMedia)
        .where(ProductMedia.product_id == product_id)
        .order_by(ProductMedia.position)
    )
    result = await db.execute(stmt)
    media = list(result.scalars().all())

    return [
        {
            "id": m.id,
            "media_type": m.media_type.value if hasattr(m.media_type, 'value') else m.media_type,
            "path": m.path,
            "telegram_file_id": m.telegram_file_id,
            "position": m.position,
        }
        for m in media
    ]


# ── User point session ────────────────────────────────

@router.get("/user-point-session")
async def get_user_point_session(
    telegram_id: int = Query(...),
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Проверить выбрана ли точка у покупателя."""
    org_user = await _get_org_user(db, telegram_id, org_id)
    if not org_user:
        return {"error": True, "detail": "User not found"}

    session = await extras.get_user_point(db, org_user.id)
    if not session:
        return {"error": True, "detail": "No point selected"}

    return {
        "org_user_id": session.org_user_id,
        "point_id": session.point_id,
    }


class CancelOrderRequest(BaseModel):
    telegram_id: int
    order_id: int


@router.post("/cancel-order")
async def cancel_order(
    data: CancelOrderRequest,
    org_id: int = Depends(get_service_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Отмена заказа покупателем.
    Работает только если статус = pending (ещё не подтверждён менеджером).
    """
    org_user = await _get_org_user(db, data.telegram_id, org_id)
    if not org_user:
        return {"error": True, "detail": "User not found"}

    # Проверяем что заказ принадлежит этому покупателю
    order = await order_service.get_order_by_id(db, data.order_id, org_id)
    if order.org_user_id != org_user.id:
        return {"error": True, "detail": "This is not your order"}

    # Отменить можно только pending
    if order.status.value != "pending":
        return {"error": True, "detail": "Order can only be cancelled before confirmation"}

    from app.schemas import OrderStatusChange
    await order_service.change_order_status(
        db, data.order_id, org_id,
        OrderStatusChange(new_status="cancelled", comment="Cancelled by customer"),
    )

    return {"ok": True}