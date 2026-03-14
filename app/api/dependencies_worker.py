# Файл: app/api/dependencies_worker.py
# Назначение:
# Dependencies для сотрудников (workers) и проверки их permissions.

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import verify_token
from app.models.worker import Worker

security = HTTPBearer()


async def get_current_worker(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Worker:
    """
    Получает текущего сотрудника из JWT.
    """

    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # JWT должен иметь type="worker"
    if payload.get("type") != "worker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker token required",
        )

    worker_id = payload.get("sub")

    # Сразу подгружаем роль, чтобы потом безопасно читать permissions.
    stmt = (
        select(Worker)
        .where(Worker.id == int(worker_id))
        .options(selectinload(Worker.role))
    )
    result = await db.execute(stmt)

    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker not found",
        )

    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker is inactive",
        )

    return worker


def require_worker_permission(permission: str):
    """
    Dependency для проверки прав сотрудника.

    Пример использования:
        worker: Worker = Depends(require_worker_permission("can_edit_products"))
    """

    async def _check_permission(
        worker: Worker = Depends(get_current_worker),
    ) -> Worker:
        # Если у сотрудника нет роли — запрещаем доступ.
        if not worker.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Worker has no role assigned",
            )

        # Берём JSON с правами из роли.
        permissions = worker.role.permissions or {}

        # Проверяем, есть ли нужное право.
        if not permissions.get(permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )

        return worker

    return _check_permission