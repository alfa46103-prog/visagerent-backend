# Файл: app/api/v1/endpoints/workers.py
# Назначение: HTTP-эндпоинты для управления сотрудниками и ролями.
#
# Все эндпоинты требуют авторизации сотрудника с правом can_manage_staff.
# org_id берётся из токена текущего сотрудника — не передаётся в URL.
# Это гарантирует мультитенантность: сотрудник видит только свою организацию.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import worker as worker_service
from app.services import worker_role as role_service
from app.schemas import (
    WorkerCreate, WorkerRead, WorkerUpdate,
    WorkerRoleCreate, WorkerRoleRead, WorkerRoleUpdate,
)

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  РОЛИ (worker_roles)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/roles", response_model=list[WorkerRoleRead])
async def get_roles(
    # require_permission возвращает текущего Worker
    # если у него есть право can_manage_staff
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Список всех ролей организации."""
    # org_id берём из текущего сотрудника — мультитенантность
    return await role_service.get_roles(db, current_worker.org_id)


@router.post("/roles", response_model=WorkerRoleRead, status_code=201)
async def create_role(
    data: WorkerRoleCreate,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Создать новую роль."""
    return await role_service.create_role(db, current_worker.org_id, data)


@router.patch("/roles/{role_id}", response_model=WorkerRoleRead)
async def update_role(
    role_id: int,
    data: WorkerRoleUpdate,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить роль (частичное обновление)."""
    return await role_service.update_role(db, role_id, current_worker.org_id, data)


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить роль. У сотрудников с этой ролью role_id станет NULL."""
    await role_service.delete_role(db, role_id, current_worker.org_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  СОТРУДНИКИ (workers)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/", response_model=list[WorkerRead])
async def get_workers(
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Список сотрудников организации."""
    return await worker_service.get_workers(db, current_worker.org_id, is_active)


@router.get("/{worker_id}", response_model=WorkerRead)
async def get_worker(
    worker_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Получить сотрудника по ID."""
    return await worker_service.get_worker_by_id(db, worker_id, current_worker.org_id)


@router.post("/", response_model=WorkerRead, status_code=201)
async def create_worker(
    data: WorkerCreate,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать нового сотрудника.

    После создания администратор должен сообщить сотруднику
    его Telegram ID, чтобы тот мог получать уведомления.
    """
    return await worker_service.create_worker(db, current_worker.org_id, data)


@router.patch("/{worker_id}", response_model=WorkerRead)
async def update_worker(
    worker_id: int,
    data: WorkerUpdate,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить данные сотрудника."""
    return await worker_service.update_worker(db, worker_id, current_worker.org_id, data)


@router.delete("/{worker_id}", response_model=WorkerRead)
async def deactivate_worker(
    worker_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    """
    Деактивировать сотрудника (мягкое удаление).
    Ставит is_active = False. Данные сохраняются для истории.
    """
    return await worker_service.deactivate_worker(db, worker_id, current_worker.org_id)