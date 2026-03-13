# Файл: app/services/audit.py
# Назначение: Сервис аудита действий.
#
# Записывает все важные действия в систему:
#   - создание/изменение/удаление товаров, заказов, сотрудников
#   - блокировка пользователей
#   - входы в систему
#   - экспорт данных
#
# Используется двумя способами:
#   1. Прямой вызов: await audit.log(db, ...) из сервисов
#   2. В будущем: middleware для автоматической записи

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog, AuditAction


async def log(
    db: AsyncSession,
    org_id: int | None,
    actor_id: int | None,
    actor_type: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Записать действие в журнал аудита.

    Параметры:
        org_id: ID организации (None для супер-админа)
        actor_id: кто совершил действие (worker.id или user.id)
        actor_type: "worker", "user", "system"
        action: "create", "update", "delete", "block", "login", "export"
        entity_type: "product", "order", "worker", "organization" и т.д.
        entity_id: ID изменённого объекта (строка, т.к. может быть UUID)
        old_data: данные ДО изменения (для update/delete)
        new_data: данные ПОСЛЕ изменения (для create/update)
        ip_address: IP-адрес клиента

    Пример вызова:
        await audit.log(
            db,
            org_id=worker.org_id,
            actor_id=worker.id,
            actor_type="worker",
            action="update",
            entity_type="product",
            entity_id=str(product.id),
            old_data={"price": 500},
            new_data={"price": 600},
        )
    """
    entry = AuditLog(
        org_id=org_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_data=old_data,
        new_data=new_data,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_logs(
    db: AsyncSession,
    org_id: int,
    entity_type: str | None = None,
    action: str | None = None,
    actor_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLog]:
    """
    Получить записи аудита с фильтрацией.

    Фильтры:
        entity_type: "product", "order" и т.д.
        action: "create", "update", "delete" и т.д.
        actor_id: ID сотрудника (кто совершил действие)
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())