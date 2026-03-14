# Файл: app/api/v1/endpoints/auth.py
# Назначение: Эндпоинты аутентификации.
#
# Два пути входа:
#   POST /auth/magic-link         — для покупателей
#   POST /auth/worker/magic-link  — для сотрудников
#   POST /auth/super-admin/magic-link — для супер-админа
#   GET  /auth/verify             — проверка magic-token -> JWT + meta для frontend

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


# ── Схемы запросов ─────────────────────────────────────

class MagicLinkRequest(BaseModel):
    """Запрос magic-link для покупателя."""
    identifier: str  # телефон или username


class WorkerLoginRequest(BaseModel):
    """Запрос magic-link для сотрудника."""
    telegram_id: int  # Telegram ID сотрудника


class SuperAdminLoginRequest(BaseModel):
    """Запрос magic-link для супер-админа."""
    telegram_id: int


# ── Схемы ответа ───────────────────────────────────────

class AuthUserResponse(BaseModel):
    """
    Минимальная информация о пользователе,
    которую frontend может сохранить в сессию.
    """
    id: int
    full_name: str | None = None
    telegram_id: int | None = None


class AuthOrgResponse(BaseModel):
    """
    Информация об организации.
    Для super_admin может быть None.
    """
    id: int
    name: str


class TokenResponse(BaseModel):
    """
    Новый ответ для frontend после проверки magic-token.

    Важно:
    теперь это не просто access_token, а полный auth-payload,
    чтобы frontend понимал:
    - кто вошёл
    - куда редиректить
    - есть ли организация
    """
    access_token: str
    token_type: str = "bearer"
    user_type: str | None = None
    redirect_to: str | None = None
    user: AuthUserResponse | None = None
    org: AuthOrgResponse | None = None
    permissions: dict[str, bool] | None = None


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
    """
    worker = await auth_service.find_worker_for_login(db, body.telegram_id)

    # Создаём токен с type="worker" — это сотрудник
    token = await auth_service.create_magic_token(db, worker.id, "worker")

    verify_url = f"http://localhost:8000/api/v1/auth/verify?token={token.token}"

    # TODO: отправить ссылку в Telegram через бота
    return {"message": "Magic link sent to Telegram", "debug_url": verify_url}


# ── Супер-админ ────────────────────────────────────────

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


# ── Общая верификация ──────────────────────────────────

@router.get("/verify", response_model=TokenResponse)
async def verify_magic_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Проверка magic-token -> полный auth-ответ для frontend.

    Раньше endpoint возвращал только строковый JWT.
    Теперь сервис возвращает уже готовый словарь с:
    - access_token
    - token_type
    - user_type
    - redirect_to
    - user / org / permissions (по мере наполнения)
    """
    auth_payload = await auth_service.verify_magic_token(db, token)

    # Важно:
    # auth_payload уже словарь нужного формата.
    # Поэтому просто распаковываем его в TokenResponse.
    return TokenResponse(**auth_payload)