# Файл: app/api/v1/endpoints/health.py
# Назначение: Простой эндпоинт для проверки доступности API.
# Не требует аутентификации, всегда возвращает 200 OK.

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """
    Проверка работоспособности API.
    Возвращает {"status": "ok"}.
    """
    return {"status": "ok"}