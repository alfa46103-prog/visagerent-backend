# Файл: app/services/permissions.py
# Назначение: Система проверки прав доступа.
#
# Как это работает:
#   1. У каждого сотрудника (Worker) есть роль (WorkerRole)
#   2. В роли хранится поле permissions (JSONB) — словарь вида:
#      {"can_edit_products": true, "can_view_orders": true, ...}
#   3. Когда сотрудник делает запрос, мы проверяем:
#      есть ли у его роли нужное разрешение?
#
# Использование в эндпоинтах:
#   @router.post("/products")
#   async def create_product(
#       worker: Worker = Depends(require_permission("can_edit_products")),
#   ):
#       ...  # сюда попадём только если у worker есть это право

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import verify_token
from app.models.worker import Worker
from app.models.worker_role import WorkerRole


security = HTTPBearer()


async def get_current_worker(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Worker:
    """
    Извлекает текущего сотрудника из JWT-токена.

    В токене хранится:
      - sub: ID сотрудника (worker.id)
      - type: "worker"

    Загружаем сотрудника вместе с его ролью (selectinload),
    чтобы потом проверить permissions без дополнительного запроса к БД.

    Ошибки:
      401 — токен невалидный, отсутствует, или сотрудник не найден
      403 — сотрудник заблокирован (is_active = false)
    """
    # Проверяем JWT-токен
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Проверяем что это токен сотрудника, а не покупателя
    user_type = payload.get("type")
    if user_type != "worker":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint requires worker authentication",
        )

    worker_id = payload.get("sub")
    if not worker_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Загружаем сотрудника из БД вместе с ролью
    # selectinload — подгружает связанную роль одним запросом
    # без этого при обращении к worker.role будет ошибка (async lazy load)
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

    # Проверяем что сотрудник активен
    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker account is deactivated",
        )

    return worker


def require_permission(permission: str):
    """
    Фабрика зависимостей — создаёт Depends-функцию для проверки конкретного права.

    Как использовать:
        @router.post("/products")
        async def create_product(
            worker: Worker = Depends(require_permission("can_edit_products")),
        ):
            # Сюда попадаем только если у сотрудника есть право can_edit_products
            ...

    Параметры:
        permission: строка — название права, например:
            "can_edit_products"
            "can_view_orders"
            "can_confirm_orders"
            "can_manage_staff"
            "can_view_reports"
            "can_manage_stock"

    Как проверяется:
        1. Получаем текущего сотрудника (get_current_worker)
        2. Смотрим его роль (worker.role)
        3. В роли есть поле permissions (JSONB) — проверяем нужный ключ
        4. Если права нет — 403 Forbidden

    Особый случай:
        Если у роли permissions = {"is_admin": true},
        то сотрудник имеет ВСЕ права (как суперпользователь организации).
    """

    async def _check_permission(
        worker: Worker = Depends(get_current_worker),
    ) -> Worker:
        # Если нет роли — нет прав
        if not worker.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No role assigned. Required permission: {permission}",
            )

        # Достаём словарь permissions из роли
        # Пример: {"can_edit_products": true, "can_view_orders": true}
        permissions = worker.role.permissions or {}

        # Админ организации имеет все права
        if permissions.get("is_admin", False):
            return worker

        # Проверяем конкретное право
        if not permissions.get(permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )

        return worker

    return _check_permission