# Файл: app/services/geocoding.py
# Назначение: Сервис геокодирования через geopy (Nominatim).
#
# Nominatim — бесплатный сервис от OpenStreetMap.
# ОГРАНИЧЕНИЕ: не более 1 запроса в секунду.
# Мы контролируем это через asyncio.Lock + sleep.
#
# Нормализация адреса:
#   Покупатель вводит: "мира 2 нижневартовск"
#   Nominatim находит координаты и сырые данные (addressdetails)
#   Мы собираем из них чистый адрес: "г. Нижневартовск, ул. Мира, д. 2"
#   Координаты сохраняем для карты

import asyncio
import time
from functools import partial

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


# Геокодер с user_agent (обязательно для Nominatim)
_geocoder = Nominatim(user_agent="visagerent-app (tg: @visageRENT)", timeout=10)

# Контроль частоты запросов: не чаще 1 раза в секунду
# asyncio.Lock гарантирует что два запроса не уйдут одновременно
_lock = asyncio.Lock()
_last_request_time: float = 0


async def _rate_limited_call(func, *args, **kwargs):
    """
    Обёртка для вызова geopy с rate limiting.

    Гарантирует минимум 1 секунду между запросами к Nominatim.
    Без этого Nominatim начнёт возвращать 429 Too Many Requests.
    """
    global _last_request_time

    async with _lock:
        # Считаем сколько прошло с последнего запроса
        now = time.monotonic()
        elapsed = now - _last_request_time

        # Если прошло меньше секунды — ждём
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)

        # Выполняем запрос в отдельном потоке (geopy синхронный)
        result = await asyncio.to_thread(partial(func, *args, **kwargs))

        # Обновляем время последнего запроса
        _last_request_time = time.monotonic()

        return result


def _normalize_address(raw: dict) -> str:
    """
    Собирает нормализованный адрес из сырых данных Nominatim.

    Nominatim возвращает в addressdetails поля:
      house_number, road, city/town/village, state, postcode ...

    Мы собираем только нужное и в правильном порядке:
      "г. Нижневартовск, ул. Мира, д. 2, 628600"

    Входной параметр raw — это location.raw от geopy,
    содержит поле "address" с разбивкой по частям.
    """
    addr = raw.get("address", {})

    parts = []

    # Город — может быть в разных полях в зависимости от размера населённого пункта
    city = (
        addr.get("city")           # крупный город
        or addr.get("town")        # город поменьше
        or addr.get("village")     # село/посёлок
        or addr.get("hamlet")      # деревня
    )
    if city:
        parts.append(f"г. {city}")

    # Улица
    road = addr.get("road")
    if road:
        parts.append(f"ул. {road}")

    # Номер дома
    house = addr.get("house_number")
    if house:
        parts.append(f"д. {house}")

    # Индекс
    postcode = addr.get("postcode")
    if postcode:
        parts.append(postcode)

    # Если не удалось разобрать — возвращаем как есть от Nominatim
    if not parts:
        return raw.get("display_name", "Адрес не определён")

    return ", ".join(parts)


async def geocode_address(address: str) -> dict | None:
    """
    Прямое геокодирование: текст → координаты + нормализованный адрес.

    Покупатель вводит: "мира 2 нижневартовск"

    Возвращает:
        {
            "normalized_address": "г. Нижневартовск, ул. Мира, д. 2, 628600",
            "full_address": "2, улица Мира, ..., Россия",
            "latitude": 60.9344,
            "longitude": 76.5531,
        }
        или None если адрес не найден.
    """
    try:
        location = await _rate_limited_call(
            _geocoder.geocode,
            address,
            language="ru",
            addressdetails=True,   # получаем разбивку по полям
        )

        if not location:
            return None

        return {
            "normalized_address": _normalize_address(location.raw),
            "full_address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "raw": location.raw,
        }

    except (GeocoderTimedOut, GeocoderServiceError):
        return None


async def reverse_geocode(latitude: float, longitude: float) -> dict | None:
    """
    Обратное геокодирование: координаты → нормализованный адрес.

    Покупатель отправляет геолокацию из Telegram.

    Возвращает:
        {
            "normalized_address": "г. Нижневартовск, ул. Мира, д. 2, 628600",
            "full_address": "2, улица Мира, ..., Россия",
            "latitude": 60.9344,
            "longitude": 76.5531,
        }
        или None если по координатам ничего не найдено.
    """
    try:
        location = await _rate_limited_call(
            _geocoder.reverse,
            (latitude, longitude),
            language="ru",
            addressdetails=True,
        )

        if not location:
            return None

        return {
            "normalized_address": _normalize_address(location.raw),
            "full_address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "raw": location.raw,
        }

    except (GeocoderTimedOut, GeocoderServiceError):
        return None