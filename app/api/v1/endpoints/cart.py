# Файл: app/api/v1/endpoints/cart.py
# Назначение: HTTP-эндпоинты корзины.
#
# Корзина работает от лица покупателя (OrganizationUser),
# но пока для тестирования через API используем worker auth.
# Когда будет Telegram-бот — корзина будет вызываться оттуда.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import cart as cart_service
from app.schemas import CartItemAdd, CartItemRead, CartItemUpdate

router = APIRouter()


@router.get("/", response_model=list[CartItemRead])
async def get_cart(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Содержимое корзины покупателя (для просмотра сотрудником)."""
    return await cart_service.get_cart(db, org_user_id)


@router.post("/", response_model=CartItemRead, status_code=201)
async def add_to_cart(
    org_user_id: int,
    data: CartItemAdd,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Добавить товар в корзину покупателя."""
    return await cart_service.add_to_cart(db, org_user_id, data)


@router.patch("/{cart_item_id}", response_model=CartItemRead)
async def update_cart_item(
    cart_item_id: int,
    org_user_id: int,
    data: CartItemUpdate,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Изменить количество товара в корзине."""
    return await cart_service.update_cart_item(db, cart_item_id, org_user_id, data)


@router.delete("/{cart_item_id}", status_code=204)
async def remove_from_cart(
    cart_item_id: int,
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить товар из корзины."""
    await cart_service.remove_from_cart(db, cart_item_id, org_user_id)


@router.delete("/clear/{org_user_id}", status_code=204)
async def clear_cart(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Очистить корзину полностью."""
    await cart_service.clear_cart(db, org_user_id)


@router.get("/validate-prices/{org_user_id}")
async def validate_cart_prices(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Проверить актуальность цен в корзине. Возвращает список расхождений."""
    return await cart_service.validate_cart_prices(db, org_user_id)


@router.post("/refresh-prices/{org_user_id}", response_model=list[CartItemRead])
async def refresh_cart_prices(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить цены в корзине до актуальных."""
    return await cart_service.refresh_cart_prices(db, org_user_id)