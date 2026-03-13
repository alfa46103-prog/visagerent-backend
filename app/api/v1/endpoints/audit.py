# Файл: app/api/v1/endpoints/audit.py
# Назначение: HTTP-эндпоинты для просмотра журнала аудита.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import audit as audit_service
from app.schemas import AuditLogRead

router = APIRouter()


@router.get("/", response_model=list[AuditLogRead])
async def get_audit_logs(
    entity_type: str | None = Query(None, description="Фильтр по типу: product, order, worker..."),
    action: str | None = Query(None, description="Фильтр по действию: create, update, delete..."),
    actor_id: int | None = Query(None, description="Фильтр по ID сотрудника"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Журнал аудита организации.

    Показывает все действия: кто, когда, что изменил.
    Доступен только администраторам.
    """
    return await audit_service.get_logs(
        db, current_worker.org_id,
        entity_type=entity_type,
        action=action,
        actor_id=actor_id,
        skip=skip,
        limit=limit,
    )