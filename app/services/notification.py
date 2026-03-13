# Файл: app/services/notification.py
# Назначение: Сервис уведомлений.
#
# Уведомления проходят через очередь (notification_queue).
# Процесс:
#   1. Событие в системе (новый заказ, смена статуса и т.д.)
#   2. Вызываем enqueue_notification — запись попадает в очередь
#   3. Фоновый Celery-воркер забирает записи и отправляет через Telegram
#
# Шаблоны хранятся в notification_templates.
# Переменные в шаблоне подставляются из payload:
#   "Заказ {order_id} на сумму {total}" + {"order_id": "ORD-123", "total": 1500}
#   → "Заказ ORD-123 на сумму 1500"

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.models.organization_user import OrganizationUser
from app.models.notification_template import NotificationTemplate, NotificationType
from app.models.notification_queue import NotificationQueue
from app.schemas import (
    NotificationTemplateCreate, NotificationTemplateUpdate,
    NotificationSend,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ШАБЛОНЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_templates(
    db: AsyncSession,
    org_id: int,
) -> list[NotificationTemplate]:
    """Все шаблоны уведомлений организации."""
    stmt = select(NotificationTemplate).where(
        NotificationTemplate.org_id == org_id,
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_template_by_id(
    db: AsyncSession,
    template_id: int,
    org_id: int,
) -> NotificationTemplate:
    """Получить шаблон по ID."""
    stmt = select(NotificationTemplate).where(
        NotificationTemplate.id == template_id,
        NotificationTemplate.org_id == org_id,
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


async def create_template(
    db: AsyncSession,
    org_id: int,
    data: NotificationTemplateCreate,
) -> NotificationTemplate:
    """
    Создать шаблон.

    Тип уведомления уникален в пределах организации
    (ограничение uq_notification_template_org_type в модели).
    """
    template = NotificationTemplate(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    db: AsyncSession,
    template_id: int,
    org_id: int,
    data: NotificationTemplateUpdate,
) -> NotificationTemplate:
    """Обновить шаблон."""
    template = await get_template_by_id(db, template_id, org_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(
    db: AsyncSession,
    template_id: int,
    org_id: int,
) -> None:
    """Удалить шаблон."""
    template = await get_template_by_id(db, template_id, org_id)
    await db.delete(template)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ОЧЕРЕДЬ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def enqueue_notification(
    db: AsyncSession,
    org_id: int,
    org_user_id: int,
    notification_type: str,
    payload: dict | None = None,
) -> NotificationQueue:
    """
    Поставить уведомление в очередь.

    Вызывается из других сервисов при событиях:
      - order.change_order_status → "order_confirmed"
      - loyalty.accrue_points    → "points_accrued"
      - и т.д.

    Параметры:
        org_user_id: кому отправить
        notification_type: тип (соответствует шаблону)
        payload: данные для подстановки в шаблон
    """
    # Ищем шаблон для этого типа уведомления
    stmt = select(NotificationTemplate).where(
        NotificationTemplate.org_id == org_id,
        NotificationTemplate.type == notification_type,
        NotificationTemplate.is_active == True,
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    # Создаём запись в очереди
    notification = NotificationQueue(
        org_id=org_id,
        org_user_id=org_user_id,
        template_id=template.id if template else None,
        type=notification_type,
        payload=payload or {},
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


def render_template(body: str, payload: dict) -> str:
    """
    Подставить переменные в шаблон.

    Шаблон: "Заказ {order_id} на сумму {total} создан!"
    Payload: {"order_id": "ORD-123", "total": 1500}
    Результат: "Заказ ORD-123 на сумму 1500 создан!"

    Если переменная не найдена в payload — оставляет как есть.
    """
    try:
        return body.format(**payload)
    except KeyError:
        # Если какой-то ключ не найден — подставляем что можем
        for key, value in payload.items():
            body = body.replace(f"{{{key}}}", str(value))
        return body


async def get_pending_notifications(
    db: AsyncSession,
    limit: int = 100,
) -> list[NotificationQueue]:
    """
    Получить неотправленные уведомления из очереди.

    Вызывается Celery-воркером каждую минуту.
    Берёт записи где sent_at IS NULL и attempts < 3.
    """
    stmt = (
        select(NotificationQueue)
        .where(
            NotificationQueue.sent_at.is_(None),
            NotificationQueue.failed_at.is_(None),
            NotificationQueue.attempts < 3,
        )
        .order_by(NotificationQueue.scheduled_at)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_as_sent(
    db: AsyncSession,
    notification_id: int,
) -> None:
    """Пометить уведомление как отправленное."""
    notification = await db.get(NotificationQueue, notification_id)
    if notification:
        notification.sent_at = datetime.now(timezone.utc)
        await db.commit()


async def mark_as_failed(
    db: AsyncSession,
    notification_id: int,
    error: str,
) -> None:
    """Пометить уведомление как неудачное."""
    notification = await db.get(NotificationQueue, notification_id)
    if notification:
        notification.attempts += 1
        notification.error = error
        # После 3 попыток — помечаем как окончательно failed
        if notification.attempts >= 3:
            notification.failed_at = datetime.now(timezone.utc)
        await db.commit()


async def get_queue(
    db: AsyncSession,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[NotificationQueue]:
    """Просмотр очереди уведомлений (для админки)."""
    stmt = (
        select(NotificationQueue)
        .where(NotificationQueue.org_id == org_id)
        .order_by(NotificationQueue.scheduled_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())





async def create_broadcast(
    db: AsyncSession,
    org_id: int,
    message: str,
    tier_id: int | None = None,
    is_active_only: bool = True,
) -> int:
    """
    Поставить массовую рассылку в очередь.

    Создаёт запись в notification_queue для каждого подходящего пользователя.
    Отправка произойдёт фоновым процессом с учётом flood control Telegram.

    Возвращает количество уведомлений в очереди.
    """
    # Собираем список получателей
    stmt = select(OrganizationUser).where(
        OrganizationUser.org_id == org_id,
    )
    if is_active_only:
        stmt = stmt.where(OrganizationUser.is_blocked == False)
    if tier_id:
        stmt = stmt.where(OrganizationUser.tier_id == tier_id)

    result = await db.execute(stmt)
    users = list(result.scalars().all())

    # Создаём уведомление для каждого пользователя
    count = 0
    for user in users:
        notification = NotificationQueue(
            org_id=org_id,
            org_user_id=user.id,
            type="promo",
            payload={"message": message},
        )
        db.add(notification)
        count += 1

    await db.commit()
    return count