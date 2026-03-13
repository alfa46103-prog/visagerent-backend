# Файл: app/api/v1/endpoints/organizations.py
# Назначение: HTTP-эндпоинты для управления организациями.
#
# Эндпоинты здесь "тонкие" — они только:
#   1. Принимают параметры запроса
#   2. Вызывают сервис (бизнес-логика)
#   3. Возвращают ответ
#
# Вся логика (проверки, запросы к БД) живёт в сервисе.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.services import organization as org_service

from app.core.security import create_access_token

from datetime import timedelta

router = APIRouter()


@router.get("/", response_model=list[OrganizationRead])
async def get_organizations(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(20, ge=1, le=100, description="Макс. записей в ответе"),
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    db: AsyncSession = Depends(get_db),
):
    """Список организаций с пагинацией и фильтрацией."""
    return await org_service.get_organizations(db, skip, limit, is_active)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить организацию по ID."""
    return await org_service.get_organization_by_id(db, org_id)


@router.post("/", response_model=OrganizationRead, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Создать новую организацию."""
    return await org_service.create_organization(db, data)


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Частичное обновление организации."""
    return await org_service.update_organization(db, org_id, data)


@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Удалить организацию."""
    await org_service.delete_organization(db, org_id)





@router.post("/{org_id}/service-token")
async def generate_service_token(
    org_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Сгенерировать сервисный токен для бота организации.

    Этот токен прописывается в .env бота.
    Бот использует его для авторизации запросов к API.

    Токен живёт 365 дней. При необходимости можно перегенерировать.

    ВАЖНО: этот эндпоинт должен быть доступен только супер-админу.
    Пока без проверки прав — добавить когда будет супер-админ middleware.
    """
    from app.services.organization import get_organization_by_id
    org = await get_organization_by_id(db, org_id)

    # Создаём JWT с type="service" и org_id внутри
    # Срок жизни — 1 год
    token = create_access_token(
        data={
            "sub": str(org.id),
            "type": "service",
            "org_id": org.id,
        },
        expires_delta=timedelta(days=365),
    )

    return {"service_token": token, "org_id": org.id, "expires_in": "365 days"}