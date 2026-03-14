# Файл: app/api/dependencies.py
# Назначение: общие зависимости для API-эндпоинтов:
# - получение текущего пользователя по JWT
# - опциональная аутентификация
# - проверка сервисного токена
# - проверка доступа пользователя к конкретной организации

from typing import Iterable

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import verify_token
from app.models.global_user import GlobalUser
from app.models.organization_user import OrganizationUser, UserRole






# Стандартная Bearer-аутентификация.
security = HTTPBearer()

# Вариант без автоматической ошибки — нужен для "опционального пользователя".
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> GlobalUser | OrganizationUser:
    """
    Извлекает текущего пользователя из JWT.

    Поддерживает два основных типа:
    - global: глобальный пользователь платформы
    - org / org_user / organization: пользователь внутри организации

    Возвращает объект SQLAlchemy-модели:
    - GlobalUser
    - OrganizationUser
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user_type = payload.get("type", "global")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub",
        )

    # Если это глобальный пользователь — ищем его в таблице global_users.
    if user_type == "global":
        stmt = select(GlobalUser).where(GlobalUser.id == int(user_id))

    # Если это пользователь организации — ищем membership в organization_users.
    elif user_type in {"org", "org_user", "organization"}:
        stmt = (
            select(OrganizationUser)
            .where(OrganizationUser.id == int(user_id))
            .options(
                # Подгружаем организацию и глобального пользователя заранее,
                # чтобы потом не словить async lazy-load.
                selectinload(OrganizationUser.organization),
                selectinload(OrganizationUser.global_user),
            )
        )

    # Для любых остальных типов сюда лучше не пускать.
    # Например service-token обрабатывается отдельно через get_service_org_id.
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported token type: {user_type}",
        )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> GlobalUser | OrganizationUser | None:
    """
    Опциональная аутентификация.

    Если токен не передан — возвращаем None.
    Если токен передан, но невалиден — тоже возвращаем None.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None


async def get_service_org_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    Извлекает org_id из сервисного токена.

    Используется для bot-to-backend запросов, когда не нужен полноценный
    пользователь из БД, а нужен именно токен организации.
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )

    if payload.get("type") != "service":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint requires a service token",
        )

    org_id = payload.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token: no org_id",
        )

    return int(org_id)


async def get_current_org_user(
    org_id: int = Path(..., description="ID организации из URL"),
    current_user: GlobalUser | OrganizationUser = Depends(get_current_user),
) -> OrganizationUser:
    """
    Возвращает текущего пользователя организации для конкретного org_id.

    Проверяет:
    - что токен относится именно к OrganizationUser
    - что membership принадлежит нужной организации
    - что пользователь не заблокирован

    Это базовая tenant-isolation dependency.
    """
    # Глобального пользователя сюда пока не пускаем.
    # Когда появится супер-админ платформы, можно будет расширить логику.
    if not isinstance(current_user, OrganizationUser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization user required",
        )

    # Проверяем, что membership относится к той организации,
    # с которой сейчас идёт работа через URL.
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this organization",
        )

    # Если пользователь заблокирован внутри организации —
    # доступ запрещён.
    if current_user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is blocked in this organization",
        )

    return current_user


def require_org_roles(*allowed_roles: UserRole):
    """
    Фабрика dependency для проверки ролей пользователя внутри организации.

    Пример использования:
        current_user: OrganizationUser = Depends(
            require_org_roles(UserRole.ADMIN, UserRole.MODERATOR)
        )

    Если роль пользователя не входит в allowed_roles — вернём 403.
    """

    allowed_roles_set = set(allowed_roles)

    async def _check_role(
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        # Если список ролей пустой — трактуем как "любой авторизованный org user".
        if not allowed_roles_set:
            return org_user

        if org_user.role not in allowed_roles_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Insufficient role. "
                    f"Allowed roles: {[role.value for role in allowed_roles_set]}"
                ),
            )

        return org_user

    return _check_role







async def get_current_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Dependency для проверки супер-админа платформы.

    Используется в endpoint'ах:
    - создание организации
    - изменение организации
    - удаление организации

    Проверяет:
    1. JWT валиден
    2. type == super_admin
    """

    token = credentials.credentials

    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    if payload.get("type") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )

    return payload