# Файл: app/api/v1/endpoints/delivery.py
# Назначение: Эндпоинты доставки: расчёт стоимости и геокодирование.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import delivery as delivery_service
from app.schemas import (
    DeliveryCalcRequest, DeliveryCalcResponse,
    AddressResolveRequest, AddressResolveResponse,
)

router = APIRouter()


@router.post("/calculate", response_model=DeliveryCalcResponse)
async def calculate_delivery(
    data: DeliveryCalcRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Рассчитать стоимость доставки.

    Вызывается при оформлении заказа.
    Если zone_id не указан — считается самовывоз (fee = 0).
    """
    result = await delivery_service.calculate_delivery_fee(
        db, data.point_id, data.zone_id, data.order_total,
    )
    return DeliveryCalcResponse(**result)


@router.post("/resolve-address", response_model=AddressResolveResponse)
async def resolve_address(
    data: AddressResolveRequest,
):
    """
    Определить и нормализовать адрес.

    Два способа:
      1. Передать текст адреса → получить координаты и очищенный адрес
      2. Передать координаты → получить текстовый адрес

    Пример запроса (текст):
        {"address_text": "москва ленина 2"}

    Пример запроса (координаты):
        {"latitude": 55.7558, "longitude": 37.6173}

    Ответ:
        {
            "formatted_address": "2, улица Ленина, Москва, 101000, Россия",
            "short_address": "д. 2, ул. Ленина, г. Москва, 101000",
            "latitude": 55.7558,
            "longitude": 37.6173
        }
    """
    result = await delivery_service.resolve_address(
        address_text=data.address_text,
        latitude=data.latitude,
        longitude=data.longitude,
    )
    return AddressResolveResponse(**result)