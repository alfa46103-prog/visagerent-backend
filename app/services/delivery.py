# Файл: app/services/delivery.py
# Назначение: Сервис расчёта стоимости доставки.
#
# Логика:
#   1. Покупатель выбирает точку и тип доставки
#   2. Если доставка — ищем подходящую зону
#   3. Рассчитываем стоимость с учётом free_from (бесплатная доставка от суммы)
#   4. Проверяем min_order (минимальная сумма для доставки)
#
# На первом этапе зона выбирается менеджером вручную.
# В перспективе — автоматически по координатам (polygon).

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.delivery_zone import DeliveryZone
from app.services import geocoding


async def calculate_delivery_fee(
    db: AsyncSession,
    point_id: int,
    zone_id: int | None,
    order_total: float,
) -> dict:
    """
    Рассчитать стоимость доставки.

    Параметры:
        point_id: точка, с которой доставляем
        zone_id: ID зоны доставки (выбирается покупателем или менеджером)
        order_total: сумма заказа (для проверки min_order и free_from)

    Возвращает:
        {
            "delivery_fee": 300.0,       # итоговая стоимость
            "zone_name": "Центр",
            "est_minutes": 30,
            "is_free": False,            # бесплатная ли доставка
            "min_order_met": True,       # пройдена ли мин. сумма
        }
    """
    # Если зона не указана — доставка бесплатная (самовывоз)
    if zone_id is None:
        return {
            "delivery_fee": 0,
            "zone_name": None,
            "est_minutes": None,
            "is_free": True,
            "min_order_met": True,
        }

    # Ищем зону
    stmt = select(DeliveryZone).where(
        DeliveryZone.id == zone_id,
        DeliveryZone.point_id == point_id,
        DeliveryZone.is_active == True,
    )
    result = await db.execute(stmt)
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(status_code=404, detail="Delivery zone not found")

    # Проверяем минимальную сумму заказа
    min_order_met = order_total >= float(zone.min_order)

    # Определяем стоимость доставки
    delivery_fee = float(zone.delivery_fee)
    is_free = False

    # Если сумма заказа >= free_from — доставка бесплатна
    if zone.free_from and order_total >= float(zone.free_from):
        delivery_fee = 0
        is_free = True

    return {
        "delivery_fee": delivery_fee,
        "zone_name": zone.name,
        "est_minutes": zone.est_minutes,
        "is_free": is_free,
        "min_order_met": min_order_met,
    }


async def resolve_address(
    address_text: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    """
    Определить и нормализовать адрес.

    Три сценария:
      1. Покупатель ввёл "мира 2 нижневартовск"
         → геокодируем → "г. Нижневартовск, ул. Мира, д. 2, 628600"
      2. Покупатель отправил геолокацию (широта/долгота)
         → обратное геокодирование → нормализованный адрес
      3. Ничего не передано → ошибка

    В БД сохраняется normalized_address + координаты.
    """
    result = None

    if latitude is not None and longitude is not None:
        result = await geocoding.reverse_geocode(latitude, longitude)

    elif address_text:
        result = await geocoding.geocode_address(address_text)

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either address text or coordinates",
        )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Address not found. Please check the input.",
        )

    return {
        "formatted_address": result["full_address"],
        "short_address": result["normalized_address"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
    }