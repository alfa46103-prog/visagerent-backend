# Файл: app/services/auth.py
# Назначение: Сервис аутентификации через magic-link.
#
# Поддерживает два типа входа:
#
# 1. Покупатель (через Telegram-бота):
#    - Бот получает telegram_id автоматически
#    - Создаём GlobalUser если его нет
#    - JWT с type="global"
#
# 2. Сотрудник (через веб-админку):
#    - Вводит свой telegram_id на странице логина
#    - Ищем Worker с таким telegram_id
#    - Отправляем magic-link в Telegram
#    - JWT с type="worker"
#
# Разница важна: get_current_worker в permissions.py
# проверяет type="worker" в токене. Покупатель не пройдёт.

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.global_user import GlobalUser
from app.models.worker import Worker
from app.models.magic_token import MagicToken
from app.core.security import create_access_token


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ПОКУПАТЕЛИ (GlobalUser) — вход через Telegram-бота
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def find_or_create_user(
    db: AsyncSession,
    identifier: str,
    telegram_id: int | None = None,
) -> GlobalUser:
    """
    Ищет или создаёт глобального пользователя (покупателя).

    Два сценария:
      1. Из бота (telegram_id передан) — создаём если нет
      2. Из API (telegram_id не передан) — только ищем
    """
    # Сценарий 1: вызов из Telegram-бота
    if telegram_id is not None:
        stmt = select(GlobalUser).where(GlobalUser.id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            is_phone = identifier.isdigit() or identifier.startswith("+")
            user = GlobalUser(
                id=telegram_id,
                username=identifier if not is_phone else None,
                phone=identifier if is_phone else None,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    # Сценарий 2: вызов из API — только поиск
    is_phone = identifier.isdigit() or identifier.startswith("+")
    if is_phone:
        stmt = select(GlobalUser).where(GlobalUser.phone == identifier)
    else:
        stmt = select(GlobalUser).where(GlobalUser.username == identifier)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found. Please start the Telegram bot first.",
        )
    return user


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  СОТРУДНИКИ (Worker) — вход в веб-админку
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def find_worker_for_login(
    db: AsyncSession,
    telegram_id: int,
) -> Worker:
    """
    Ищет сотрудника по telegram_id для входа в админку.

    Сотрудник должен быть:
      - зарегистрирован администратором (существует в таблице workers)
      - активен (is_active = True)

    Если не найден или деактивирован — ошибка.
    """
    stmt = (
        select(Worker)
        .where(Worker.telegram_id == telegram_id)
        .options(selectinload(Worker.role))  # подгружаем роль сразу
    )
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=404,
            detail="Worker with this Telegram ID not found. "
                   "Ask your administrator to add you.",
        )

    if not worker.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is deactivated. Contact administrator.",
        )

    return worker


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAGIC TOKEN — общая логика для обоих типов
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def create_magic_token(
    db: AsyncSession,
    user_id: int,
    user_type: str,
) -> MagicToken:
    """
    Создаёт одноразовый magic-token.

    Параметры:
        user_id: ID пользователя (GlobalUser.id или Worker.id)
        user_type: "global" (покупатель) или "worker" (сотрудник)

    Токен и срок действия генерируются автоматически в модели MagicToken.
    """
    token = MagicToken(
        user_id=user_id,
        user_type=user_type,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def verify_magic_token(
    db: AsyncSession,
    token_str: str,
) -> str:
    """
    Проверяет magic-token и возвращает JWT.

    Проверки:
      1. Токен существует
      2. Не использован
      3. Не просрочен

    JWT будет содержать:
      - sub: ID пользователя (строка)
      - type: "global" или "worker"

    Потом в зависимости от type:
      - get_current_user  ищет в global_users  (для бота)
      - get_current_worker ищет в workers       (для админки)
    """
    stmt = select(MagicToken).where(MagicToken.token == token_str)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=404, detail="Token not found")

    if db_token.is_used:
        raise HTTPException(status_code=400, detail="Token already used")

    if db_token.is_expired:
        raise HTTPException(status_code=400, detail="Token expired")

    # Помечаем как использованный
    db_token.used_at = datetime.now(timezone.utc)
    await db.commit()

    # Создаём JWT с типом пользователя
    access_token = create_access_token(
        data={
            "sub": str(db_token.user_id),
            "type": db_token.user_type,  # "global" или "worker"
        }
    )
    return access_token


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  СУПЕР-АДМИН
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# Список Telegram ID супер-админов (в продакшне — из конфига или БД)
# Пока захардкожен, потом вынести в settings
SUPER_ADMIN_IDS: set[int] = set()


async def find_super_admin(
    db: AsyncSession,
    telegram_id: int,
) -> GlobalUser:
    """
    Проверить что telegram_id принадлежит супер-админу.

    Супер-админ — это GlobalUser, чей telegram_id есть в списке SUPER_ADMIN_IDS.
    В продакшне список загружается из переменной окружения или отдельной таблицы.
    """
    # Проверяем что это супер-админ
    # Если список пуст — берём из конфига
    from app.core.config import settings
    super_ids = SUPER_ADMIN_IDS
    if hasattr(settings, "SUPER_ADMIN_IDS"):
        super_ids = set(settings.SUPER_ADMIN_IDS)

    if telegram_id not in super_ids:
        raise HTTPException(
            status_code=403,
            detail="You are not a super admin",
        )

    # Находим или создаём GlobalUser
    stmt = select(GlobalUser).where(GlobalUser.id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = GlobalUser(id=telegram_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user