# Файл: app/api/v1/endpoints/organizations.py
# Назначение: HTTP-эндпоинты для управления организациями.
#
# Здесь остаются "тонкие" эндпоинты:
# - принимают параметры
# - вызывают сервис
# - возвращают ответ
#
# Но теперь мы добавляем базовую защиту по ролям внутри организации.

from datetime import timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import worker as worker_service
from app.services import worker_role as role_service
from app.services import point_worker as point_worker_service

from app.schemas import (
    WorkerCreate,
    WorkerRead,
    WorkerUpdate,
    WorkerRoleCreate,
    WorkerRoleRead,
    WorkerRoleUpdate,
    PointWorkerCreate,
    PointWorkerRead,
)

# Сервис точек организации
from app.services import point as point_service

# Схемы точек
from app.schemas import PointCreate, PointRead, PointUpdate

from app.api.dependencies import require_org_roles, get_current_super_admin
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.organization_user import OrganizationUser, UserRole
from app.schemas import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.services import organization as org_service

router = APIRouter()


@router.get("/", response_model=list[OrganizationRead])
async def get_organizations(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(20, ge=1, le=100, description="Макс. записей в ответе"),
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    db: AsyncSession = Depends(get_db),
):
    """
    Список организаций.

    TODO:
    По-хорошему этот эндпоинт должен быть доступен только супер-админу платформы,
    потому что список всех организаций — это platform-level операция.
    Пока оставляем как есть, чтобы не ломать текущий flow.
    """
    return await org_service.get_organizations(db, skip, limit, is_active)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить организацию по ID.

    Доступно только супер-админу платформы.
    """
    return await org_service.get_organization_by_id(db, org_id)


@router.post("/", response_model=OrganizationRead, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую организацию.

    Доступно только супер-админу платформы.
    """

    return await org_service.create_organization(db, data)


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Частично обновить организацию.

    Доступно только супер-админу.
    """

    return await org_service.update_organization(db, org_id, data)


@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    org_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить организацию.

    Доступно только супер-админу.
    """

    await org_service.delete_organization(db, org_id)


@router.post("/{org_id}/service-token")
async def generate_service_token(
    org_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Сгенерировать service-token для Telegram-бота организации.

    Доступно только супер-админу платформы.
    """
    org = await org_service.get_organization_by_id(db, org_id)

    token = create_access_token(
        data={
            "sub": str(org.id),
            "type": "service",
            "org_id": org.id,
        },
        expires_delta=timedelta(days=365),
    )

    return {
        "service_token": token,
        "org_id": org.id,
        "expires_in": "365 days",
    }

# ──────────────────────────────────────────────────────
#  POINTS внутри организации (platform-level access)
# ──────────────────────────────────────────────────────

@router.get("/{org_id}/points", response_model=list[PointRead])
async def get_organization_points(
    org_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить все точки конкретной организации.

    Это platform-level endpoint:
    супер-админ смотрит точки в контексте магазина.
    """
    return await point_service.get_points(db, org_id)


@router.post("/{org_id}/points", response_model=PointRead, status_code=201)
async def create_organization_point(
    org_id: int,
    data: PointCreate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую точку внутри организации.

    Доступно только супер-админу.
    """
    return await point_service.create_point(db, org_id, data)


@router.patch("/{org_id}/points/{point_id}", response_model=PointRead)
async def update_organization_point(
    org_id: int,
    point_id: int,
    data: PointUpdate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Изменить точку внутри организации.

    Важно:
    point_id должен принадлежать именно этой организации.
    """
    return await point_service.update_point(db, point_id, org_id, data)


# ──────────────────────────────────────────────────────
#  ROLES внутри организации (platform-level access)
# ──────────────────────────────────────────────────────

@router.get("/{org_id}/roles", response_model=list[WorkerRoleRead])
async def get_organization_roles(
    org_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить все роли сотрудников организации.
    """
    return await role_service.get_roles(db, org_id)


@router.post("/{org_id}/roles", response_model=WorkerRoleRead, status_code=201)
async def create_organization_role(
    org_id: int,
    data: WorkerRoleCreate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать роль сотрудника внутри организации.
    """
    return await role_service.create_role(db, org_id, data)


@router.patch("/{org_id}/roles/{role_id}", response_model=WorkerRoleRead)
async def update_organization_role(
    org_id: int,
    role_id: int,
    data: WorkerRoleUpdate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить роль сотрудника внутри организации.
    """
    return await role_service.update_role(db, role_id, org_id, data)


@router.delete("/{org_id}/roles/{role_id}", status_code=204)
async def delete_organization_role(
    org_id: int,
    role_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить роль сотрудника внутри организации.
    """
    await role_service.delete_role(db, role_id, org_id)

# ──────────────────────────────────────────────────────
#  WORKERS внутри организации (platform-level access)
# ──────────────────────────────────────────────────────

@router.get("/{org_id}/workers", response_model=list[WorkerRead])
async def get_organization_workers(
    org_id: int,
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить сотрудников организации.
    """
    return await worker_service.get_workers(db, org_id, is_active)


@router.get("/{org_id}/workers/{worker_id}", response_model=WorkerRead)
async def get_organization_worker(
    org_id: int,
    worker_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить одного сотрудника организации по ID.
    """
    return await worker_service.get_worker_by_id(db, worker_id, org_id)


@router.post("/{org_id}/workers", response_model=WorkerRead, status_code=201)
async def create_organization_worker(
    org_id: int,
    data: WorkerCreate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать сотрудника внутри организации.
    """
    return await worker_service.create_worker(db, org_id, data)


@router.patch("/{org_id}/workers/{worker_id}", response_model=WorkerRead)
async def update_organization_worker(
    org_id: int,
    worker_id: int,
    data: WorkerUpdate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить сотрудника внутри организации.
    """
    return await worker_service.update_worker(db, worker_id, org_id, data)


@router.delete("/{org_id}/workers/{worker_id}", response_model=WorkerRead)
async def deactivate_organization_worker(
    org_id: int,
    worker_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Деактивировать сотрудника внутри организации.
    """
    return await worker_service.deactivate_worker(db, worker_id, org_id)


# ──────────────────────────────────────────────────────
#  POINT-WORKER BINDINGS внутри организации
# ──────────────────────────────────────────────────────

@router.get("/{org_id}/points/{point_id}/workers", response_model=list[PointWorkerRead])
async def get_organization_point_workers(
    org_id: int,
    point_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить сотрудников, привязанных к точке.
    """
    return await point_worker_service.get_point_workers(db, org_id, point_id)


@router.post(
    "/{org_id}/points/{point_id}/workers",
    response_model=PointWorkerRead,
    status_code=201,
)
async def assign_organization_worker_to_point(
    org_id: int,
    point_id: int,
    data: PointWorkerCreate,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Привязать сотрудника к точке.
    """
    return await point_worker_service.assign_worker_to_point(
        db, org_id, point_id, data
    )


@router.patch(
    "/{org_id}/points/{point_id}/workers/{point_worker_id}",
    response_model=PointWorkerRead,
)
async def update_organization_point_worker(
    org_id: int,
    point_id: int,
    point_worker_id: int,
    is_primary: bool,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить привязку сотрудника к точке.
    Пока поддерживаем смену флага is_primary.
    """
    return await point_worker_service.update_point_worker(
        db,
        org_id,
        point_id,
        point_worker_id,
        is_primary,
    )


@router.delete(
    "/{org_id}/points/{point_id}/workers/{point_worker_id}",
    status_code=204,
)
async def remove_organization_worker_from_point(
    org_id: int,
    point_id: int,
    point_worker_id: int,
    _: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Снять сотрудника с точки.
    """
    await point_worker_service.remove_worker_from_point(
        db,
        org_id,
        point_id,
        point_worker_id,
    )