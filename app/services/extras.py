# Файл: app/services/extras.py
# Назначение: Сервисы для вспомогательных сущностей.
#
# Собраны в один файл потому что каждый из них маленький (CRUD без сложной логики).
# Если какой-то вырастет — выносим в отдельный файл.

from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.delivery_zone import DeliveryZone
from app.models.point_worker import PointWorker
from app.models.point import Point
from app.models.payment_method import PaymentMethod
from app.models.product_tag import ProductTag
from app.models.cash_register import CashRegister
from app.models.user_address import UserAddress
from app.models.user_point_session import UserPointSession
from app.models.faq import Faq
from app.models.link import Link
from app.models.referral_code import ReferralCode

import secrets


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DELIVERY ZONES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_delivery_zones(db: AsyncSession, point_id: int) -> list[DeliveryZone]:
    stmt = select(DeliveryZone).where(DeliveryZone.point_id == point_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_delivery_zone(db: AsyncSession, point_id: int, org_id: int, data) -> DeliveryZone:
    # Проверяем что точка наша
    point = await db.execute(select(Point).where(Point.id == point_id, Point.org_id == org_id))
    if not point.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Point not found")

    zone = DeliveryZone(point_id=point_id, **data.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


async def update_delivery_zone(db: AsyncSession, zone_id: int, point_id: int, data) -> DeliveryZone:
    stmt = select(DeliveryZone).where(DeliveryZone.id == zone_id, DeliveryZone.point_id == point_id)
    result = await db.execute(stmt)
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Delivery zone not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    await db.commit()
    await db.refresh(zone)
    return zone


async def delete_delivery_zone(db: AsyncSession, zone_id: int, point_id: int) -> None:
    stmt = select(DeliveryZone).where(DeliveryZone.id == zone_id, DeliveryZone.point_id == point_id)
    result = await db.execute(stmt)
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Delivery zone not found")
    await db.delete(zone)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  POINT WORKERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_point_workers(db: AsyncSession, point_id: int) -> list[PointWorker]:
    stmt = select(PointWorker).where(PointWorker.point_id == point_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_worker_to_point(db: AsyncSession, point_id: int, org_id: int, data) -> PointWorker:
    point = await db.execute(select(Point).where(Point.id == point_id, Point.org_id == org_id))
    if not point.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Point not found")

    pw = PointWorker(point_id=point_id, worker_id=data.worker_id, is_primary=data.is_primary)
    db.add(pw)
    await db.commit()
    await db.refresh(pw)
    return pw


async def remove_worker_from_point(db: AsyncSession, point_worker_id: int) -> None:
    pw = await db.get(PointWorker, point_worker_id)
    if not pw:
        raise HTTPException(status_code=404, detail="Point worker link not found")
    await db.delete(pw)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PAYMENT METHODS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_payment_methods(db: AsyncSession, org_id: int) -> list[PaymentMethod]:
    stmt = select(PaymentMethod).where(PaymentMethod.org_id == org_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_payment_method(db: AsyncSession, org_id: int, data) -> PaymentMethod:
    method = PaymentMethod(org_id=org_id, **data.model_dump())
    db.add(method)
    await db.commit()
    await db.refresh(method)
    return method


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PRODUCT TAGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_tags(db: AsyncSession, org_id: int) -> list[ProductTag]:
    stmt = select(ProductTag).where(ProductTag.org_id == org_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_tag(db: AsyncSession, org_id: int, data) -> ProductTag:
    tag = ProductTag(org_id=org_id, **data.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag_id: int, org_id: int) -> None:
    stmt = select(ProductTag).where(ProductTag.id == tag_id, ProductTag.org_id == org_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.delete(tag)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CASH REGISTERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_cash_registers(db: AsyncSession, point_id: int) -> list[CashRegister]:
    stmt = select(CashRegister).where(CashRegister.point_id == point_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_cash_register(db: AsyncSession, org_id: int, data) -> CashRegister:
    # Проверяем точку
    point = await db.execute(select(Point).where(Point.id == data.point_id, Point.org_id == org_id))
    if not point.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Point not found")

    cr = CashRegister(point_id=data.point_id, name=data.name, balance=data.balance)
    db.add(cr)
    await db.commit()
    await db.refresh(cr)
    return cr


async def adjust_cash_register(db: AsyncSession, register_id: int, data) -> CashRegister:
    cr = await db.get(CashRegister, register_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Cash register not found")

    new_balance = float(cr.balance) + data.amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient cash balance")

    cr.balance = new_balance
    await db.commit()
    await db.refresh(cr)
    return cr


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  USER ADDRESSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_user_addresses(db: AsyncSession, org_user_id: int) -> list[UserAddress]:
    stmt = select(UserAddress).where(UserAddress.org_user_id == org_user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_user_address(db: AsyncSession, org_user_id: int, data) -> UserAddress:
    addr = UserAddress(org_user_id=org_user_id, **data.model_dump())
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return addr


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  USER POINT SESSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def set_user_point(db: AsyncSession, org_user_id: int, point_id: int) -> UserPointSession:
    """Установить или обновить выбранную точку покупателя."""
    stmt = select(UserPointSession).where(UserPointSession.org_user_id == org_user_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if session:
        session.point_id = point_id
        session.selected_at = datetime.now(timezone.utc)
    else:
        session = UserPointSession(
            org_user_id=org_user_id,
            point_id=point_id,
            selected_at=datetime.now(timezone.utc),
        )
        db.add(session)

    await db.commit()
    await db.refresh(session)
    return session


async def get_user_point(db: AsyncSession, org_user_id: int) -> UserPointSession | None:
    stmt = select(UserPointSession).where(UserPointSession.org_user_id == org_user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFERRAL CODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_or_create_referral_code(db: AsyncSession, org_user_id: int) -> ReferralCode:
    """Получить реферальный код покупателя. Если нет — создать."""
    stmt = select(ReferralCode).where(
        ReferralCode.org_user_id == org_user_id,
        ReferralCode.is_active == True,
    )
    result = await db.execute(stmt)
    code = result.scalar_one_or_none()

    if not code:
        # Генерируем уникальный код: 8 символов, буквы + цифры
        code_str = secrets.token_urlsafe(6).upper()[:8]
        code = ReferralCode(
            org_user_id=org_user_id,
            code=code_str,
        )
        db.add(code)
        await db.commit()
        await db.refresh(code)

    return code


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FAQ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_faqs(db: AsyncSession, org_id: int) -> list[Faq]:
    stmt = select(Faq).where(Faq.org_id == org_id).order_by(Faq.priority)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_faq(db: AsyncSession, org_id: int, data) -> Faq:
    faq = Faq(org_id=org_id, **data.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


async def update_faq(db: AsyncSession, faq_id: int, org_id: int, data) -> Faq:
    stmt = select(Faq).where(Faq.id == faq_id, Faq.org_id == org_id)
    result = await db.execute(stmt)
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(faq, field, value)
    await db.commit()
    await db.refresh(faq)
    return faq


async def delete_faq(db: AsyncSession, faq_id: int, org_id: int) -> None:
    stmt = select(Faq).where(Faq.id == faq_id, Faq.org_id == org_id)
    result = await db.execute(stmt)
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    await db.delete(faq)
    await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LINKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_links(db: AsyncSession, org_id: int) -> list[Link]:
    stmt = select(Link).where(Link.org_id == org_id).order_by(Link.priority)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_link(db: AsyncSession, org_id: int, data) -> Link:
    link = Link(org_id=org_id, **data.model_dump())
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def delete_link(db: AsyncSession, link_id: int, org_id: int) -> None:
    stmt = select(Link).where(Link.id == link_id, Link.org_id == org_id)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.delete(link)
    await db.commit()