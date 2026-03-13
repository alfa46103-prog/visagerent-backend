# Файл: app/services/worker_role.py
# Назначение: Сервис для управления ролями сотрудников.
#
# Роль — это набор прав (permissions), который назначается сотруднику.
# Примеры ролей: "Администратор", "Менеджер", "Кладовщик".
#
# Все операции фильтруются по org_id — мультитенантность.
# Администратор одной организации не видит роли другой.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.worker_role import WorkerRole
from app.schemas import WorkerRoleCreate, WorkerRoleUpdate


async def get_roles(
    db: AsyncSession,
    org_id: int,
) -> list[WorkerRole]:
    """
    Получить все роли организации.

    Параметры:
        org_id: ID организации (берётся из токена текущего сотрудника)
    """
    stmt = select(WorkerRole).where(WorkerRole.org_id == org_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_role_by_id(
    db: AsyncSession,
    role_id: int,
    org_id: int,
) -> WorkerRole:
    """
    Получить роль по ID.

    Обязательно проверяем что роль принадлежит нашей организации.
    Без этой проверки сотрудник организации A мог бы
    читать роли организации B, подставив чужой role_id.
    """
    stmt = select(WorkerRole).where(
        WorkerRole.id == role_id,
        WorkerRole.org_id == org_id,  # мультитенантная проверка
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


async def create_role(
    db: AsyncSession,
    org_id: int,
    data: WorkerRoleCreate,
) -> WorkerRole:
    """
    Создать новую роль в организации.

    Название роли должно быть уникальным в пределах организации
    (ограничение uq_worker_role_name в модели).
    """
    # Проверяем уникальность имени роли в этой организации
    stmt = select(WorkerRole).where(
        WorkerRole.org_id == org_id,
        WorkerRole.name == data.name,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Role '{data.name}' already exists in this organization",
        )

    role = WorkerRole(
        org_id=org_id,
        **data.model_dump(),
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def update_role(
    db: AsyncSession,
    role_id: int,
    org_id: int,
    data: WorkerRoleUpdate,
) -> WorkerRole:
    """
    Обновить роль (PATCH — частичное обновление).

    exclude_unset=True — обновляем только переданные поля.
    Если передали только {"permissions": {...}}, то name не изменится.
    """
    role = await get_role_by_id(db, role_id, org_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)

    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(
    db: AsyncSession,
    role_id: int,
    org_id: int,
) -> None:
    """
    Удалить роль.

    В модели Worker поле role_id имеет ondelete="SET NULL",
    то есть при удалении роли у сотрудников role_id станет NULL,
    а не удалятся сами сотрудники.
    """
    role = await get_role_by_id(db, role_id, org_id)
    await db.delete(role)
    await db.commit()


async def create_default_roles(
    db: AsyncSession,
    org_id: int,
) -> list[WorkerRole]:
    """
    Создать предопределённые роли при создании новой организации.

    Вызывается автоматически из OrganizationService при создании организации.
    Администратор потом может их переименовать или изменить права.

    Создаются три роли:
      - Администратор (is_admin: true — полный доступ)
      - Менеджер (заказы, клиенты, отчёты)
      - Кладовщик (склад, закупки)
    """
    default_roles = [
        {
            "name": "Администратор",
            "description": "Полный доступ ко всем функциям",
            "permissions": {
                "is_admin": True,  # специальный флаг — все права
            },
        },
        {
            "name": "Менеджер",
            "description": "Работа с заказами, клиентами и отчётами",
            "permissions": {
                "can_view_orders": True,
                "can_confirm_orders": True,
                "can_cancel_orders": True,
                "can_view_products": True,
                "can_view_clients": True,
                "can_view_reports": True,
                "can_send_notifications": True,
            },
        },
        {
            "name": "Кладовщик",
            "description": "Управление складом и закупками",
            "permissions": {
                "can_view_products": True,
                "can_manage_stock": True,
                "can_view_purchases": True,
                "can_create_purchases": True,
            },
        },
    ]

    created_roles = []
    for role_data in default_roles:
        role = WorkerRole(org_id=org_id, **role_data)
        db.add(role)
        created_roles.append(role)

    # Один коммит на все три роли — эффективнее чем три отдельных
    await db.commit()

    # Обновляем объекты чтобы получить id и timestamps
    for role in created_roles:
        await db.refresh(role)

    return created_roles