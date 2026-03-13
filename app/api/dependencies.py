# Файл: app/api/dependencies.py
# Назначение: Общие зависимости для эндпоинтов (получение текущего пользователя и т.д.)

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_token
from app.models.global_user import GlobalUser
from app.models.organization_user import OrganizationUser

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> GlobalUser | OrganizationUser:
    """
    Извлекает и проверяет JWT токен, возвращает объект пользователя.
    Поддерживает как глобальных, так и организационных пользователей.
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
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if user_type == "global":
        stmt = select(GlobalUser).where(GlobalUser.id == int(user_id))
    else:  # org user
        stmt = select(OrganizationUser).where(OrganizationUser.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> GlobalUser | OrganizationUser | None:
    """
    Опциональная аутентификация — если токена нет, возвращает None.
    auto_error=False позволяет не выбрасывать 403 при отсутствии токена.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
    

async def get_service_org_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    Извлекает org_id из сервисного токена бота.

    Используется в эндпоинтах которые бот вызывает от имени организации.
    Не требует загрузки пользователя из БД — просто проверяет JWT.
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