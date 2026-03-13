# Файл: app/api/v1/endpoints/notifications.py
# Назначение: HTTP-эндпоинты для шаблонов и очереди уведомлений.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import notification as notif_service
from app.schemas import (
    NotificationTemplateCreate, NotificationTemplateRead, NotificationTemplateUpdate,
    NotificationQueueRead, NotificationSend, BroadcastRequest
)

router = APIRouter()


# ── Шаблоны ────────────────────────────────────────────

@router.get("/templates", response_model=list[NotificationTemplateRead])
async def get_templates(
    current_worker: Worker = Depends(require_permission("can_send_notifications")),
    db: AsyncSession = Depends(get_db),
):
    """Список шаблонов уведомлений."""
    return await notif_service.get_templates(db, current_worker.org_id)


@router.post("/templates", response_model=NotificationTemplateRead, status_code=201)
async def create_template(
    data: NotificationTemplateCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Создать шаблон."""
    return await notif_service.create_template(db, current_worker.org_id, data)


@router.patch("/templates/{template_id}", response_model=NotificationTemplateRead)
async def update_template(
    template_id: int,
    data: NotificationTemplateUpdate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Обновить шаблон."""
    return await notif_service.update_template(db, template_id, current_worker.org_id, data)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Удалить шаблон."""
    await notif_service.delete_template(db, template_id, current_worker.org_id)


# ── Очередь ────────────────────────────────────────────

@router.get("/queue", response_model=list[NotificationQueueRead])
async def get_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_worker: Worker = Depends(require_permission("can_send_notifications")),
    db: AsyncSession = Depends(get_db),
):
    """Просмотр очереди уведомлений."""
    return await notif_service.get_queue(db, current_worker.org_id, skip, limit)


@router.post("/send", response_model=NotificationQueueRead)
async def send_notification(
    data: NotificationSend,
    current_worker: Worker = Depends(require_permission("can_send_notifications")),
    db: AsyncSession = Depends(get_db),
):
    """Поставить уведомление в очередь вручную."""
    return await notif_service.enqueue_notification(
        db, current_worker.org_id,
        data.org_user_id, data.type, data.payload,
    )




@router.post("/broadcast")
async def create_broadcast(
    data: BroadcastRequest,
    current_worker: Worker = Depends(require_permission("can_send_notifications")),
    db: AsyncSession = Depends(get_db),
):
    """
    Массовая рассылка сообщений.
    Ставит уведомление в очередь для каждого подходящего пользователя.
    """
    count = await notif_service.create_broadcast(
        db, current_worker.org_id,
        message=data.message,
        tier_id=data.tier_id,
        is_active_only=data.is_active_only,
    )
    return {"queued": count, "message": f"Broadcast queued for {count} users"}