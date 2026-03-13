# Файл: app/api/v1/endpoints/auth.py
# Назначение: Эндпоинты аутентификации.
#
# Два пути входа:
#   POST /auth/magic-link         — для покупателей (из бота)
#   POST /auth/worker/magic-link  — для сотрудников (из веб-админки)
#   GET  /auth/verify             — общий: проверка токена → JWT

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


# ── Схемы ──────────────────────────────────────────────

class MagicLinkRequest(BaseModel):
    """Запрос magic-link для покупателя."""
    identifier: str  # телефон или username


class WorkerLoginRequest(BaseModel):
    """Запрос magic-link для сотрудника."""
    telegram_id: int  # Telegram ID сотрудника


class TokenResponse(BaseModel):
    """Ответ с JWT."""
    access_token: str
    token_type: str = "bearer"


# ── Покупатель ─────────────────────────────────────────

@router.post("/magic-link")
async def request_magic_link(
    body: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Magic-link для покупателя.
    Вызывается из Telegram-бота.
    """
    user = await auth_service.find_or_create_user(db, body.identifier)

    # Создаём токен с type="global" — это покупатель
    token = await auth_service.create_magic_token(db, user.id, "global")

    verify_url = f"http://localhost:8000/api/v1/auth/verify?token={token.token}"

    # TODO: отправить ссылку в Telegram
    return {"message": "Magic link created", "debug_url": verify_url}


# ── Сотрудник ──────────────────────────────────────────

@router.post("/worker/magic-link")
async def request_worker_magic_link(
    body: WorkerLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Magic-link для сотрудника (вход в веб-админку).

    Процесс:
      1. Сотрудник вводит свой Telegram ID на странице логина
      2. Бэкенд находит Worker с этим telegram_id
      3. Создаёт magic-token
      4. Отправляет ссылку в Telegram (пока возвращаем в ответе)
      5. Сотрудник переходит по ссылке → GET /auth/verify → JWT
    """
    # Ищем сотрудника — если не найден или деактивирован, будет ошибка
    worker = await auth_service.find_worker_for_login(db, body.telegram_id)

    # Создаём токен с type="worker" — это сотрудник
    token = await auth_service.create_magic_token(db, worker.id, "worker")

    verify_url = f"http://localhost:8000/api/v1/auth/verify?token={token.token}"

    # TODO: отправить ссылку в Telegram через бота
    # await bot.send_message(worker.telegram_id, f"Войти в админку: {verify_url}")

    return {"message": "Magic link sent to Telegram", "debug_url": verify_url}


# ── Общая верификация ──────────────────────────────────

@router.get("/verify", response_model=TokenResponse)
async def verify_magic_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Проверка magic-token → JWT.

    Общий для покупателей и сотрудников.
    Тип пользователя (global/worker) зашит внутри magic-token,
    и попадёт в JWT автоматически.
    """
    access_token = await auth_service.verify_magic_token(db, token)
    return TokenResponse(access_token=access_token)


class SuperAdminLoginRequest(BaseModel):
    """Запрос magic-link для супер-админа."""
    telegram_id: int


@router.post("/super-admin/magic-link")
async def request_super_admin_magic_link(
    body: SuperAdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Magic-link для супер-администратора.

    Проверяет что telegram_id есть в списке SUPER_ADMIN_IDS.
    JWT будет с type="super_admin".
    """
    user = await auth_service.find_super_admin(db, body.telegram_id)
    token = await auth_service.create_magic_token(db, user.id, "super_admin")
    verify_url = f"http://localhost:8000/api/v1/auth/verify?token={token.token}"

    return {"message": "Magic link for super admin", "debug_url": verify_url}

