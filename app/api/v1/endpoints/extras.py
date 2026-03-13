# Файл: app/api/v1/endpoints/extras.py
# Назначение: Эндпоинты для вспомогательных сущностей.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.worker import Worker
from app.services.permissions import require_permission
from app.services import extras
from app.services import price_list as pl_service
from app.schemas import (
    DeliveryZoneCreate, DeliveryZoneRead, DeliveryZoneUpdate,
    PointWorkerCreate, PointWorkerRead,
    PaymentMethodCreate, PaymentMethodRead,
    ProductTagCreate, ProductTagRead,
    CashRegisterCreate, CashRegisterRead, CashRegisterAdjust,
    UserAddressCreate, UserAddressRead,
    UserPointSessionRead, UserPointSessionSet,
    ReferralCodeRead,
    FaqCreate, FaqRead, FaqUpdate,
    LinkCreate, LinkRead,
    PriceListCreate, PriceListRead,
    PriceListItemCreate, PriceListItemRead,
)




router = APIRouter()


# ── Delivery Zones ─────────────────────────────────────

@router.get("/points/{point_id}/zones", response_model=list[DeliveryZoneRead])
async def get_delivery_zones(
    point_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_delivery_zones(db, point_id)


@router.post("/points/{point_id}/zones", response_model=DeliveryZoneRead, status_code=201)
async def create_delivery_zone(
    point_id: int,
    data: DeliveryZoneCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.create_delivery_zone(db, point_id, current_worker.org_id, data)


@router.patch("/points/{point_id}/zones/{zone_id}", response_model=DeliveryZoneRead)
async def update_delivery_zone(
    point_id: int,
    zone_id: int,
    data: DeliveryZoneUpdate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.update_delivery_zone(db, zone_id, point_id, data)


@router.delete("/points/{point_id}/zones/{zone_id}", status_code=204)
async def delete_delivery_zone(
    point_id: int,
    zone_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    await extras.delete_delivery_zone(db, zone_id, point_id)


# ── Point Workers ──────────────────────────────────────

@router.get("/points/{point_id}/workers", response_model=list[PointWorkerRead])
async def get_point_workers(
    point_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_point_workers(db, point_id)


@router.post("/points/{point_id}/workers", response_model=PointWorkerRead, status_code=201)
async def add_worker_to_point(
    point_id: int,
    data: PointWorkerCreate,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.add_worker_to_point(db, point_id, current_worker.org_id, data)


@router.delete("/point-workers/{point_worker_id}", status_code=204)
async def remove_worker_from_point(
    point_worker_id: int,
    current_worker: Worker = Depends(require_permission("can_manage_staff")),
    db: AsyncSession = Depends(get_db),
):
    await extras.remove_worker_from_point(db, point_worker_id)


# ── Payment Methods ────────────────────────────────────

@router.get("/payment-methods", response_model=list[PaymentMethodRead])
async def get_payment_methods(
    current_worker: Worker = Depends(require_permission("can_view_orders")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_payment_methods(db, current_worker.org_id)


@router.post("/payment-methods", response_model=PaymentMethodRead, status_code=201)
async def create_payment_method(
    data: PaymentMethodCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.create_payment_method(db, current_worker.org_id, data)


# ── Product Tags ───────────────────────────────────────

@router.get("/tags", response_model=list[ProductTagRead])
async def get_tags(
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_tags(db, current_worker.org_id)


@router.post("/tags", response_model=ProductTagRead, status_code=201)
async def create_tag(
    data: ProductTagCreate,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.create_tag(db, current_worker.org_id, data)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int,
    current_worker: Worker = Depends(require_permission("can_edit_products")),
    db: AsyncSession = Depends(get_db),
):
    await extras.delete_tag(db, tag_id, current_worker.org_id)


# ── Cash Registers ─────────────────────────────────────

@router.get("/points/{point_id}/cash-registers", response_model=list[CashRegisterRead])
async def get_cash_registers(
    point_id: int,
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_cash_registers(db, point_id)


@router.post("/cash-registers", response_model=CashRegisterRead, status_code=201)
async def create_cash_register(
    data: CashRegisterCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.create_cash_register(db, current_worker.org_id, data)


@router.post("/cash-registers/{register_id}/adjust", response_model=CashRegisterRead)
async def adjust_cash_register(
    register_id: int,
    data: CashRegisterAdjust,
    current_worker: Worker = Depends(require_permission("can_view_reports")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.adjust_cash_register(db, register_id, data)


# ── User Addresses ─────────────────────────────────────

@router.get("/users/{org_user_id}/addresses", response_model=list[UserAddressRead])
async def get_user_addresses(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_clients")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_user_addresses(db, org_user_id)


# ── User Point Session ─────────────────────────────────

@router.get("/users/{org_user_id}/point-session", response_model=UserPointSessionRead | None)
async def get_user_point_session(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_clients")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_user_point(db, org_user_id)


# ── Referral Codes ─────────────────────────────────────

@router.get("/users/{org_user_id}/referral", response_model=ReferralCodeRead)
async def get_referral_code(
    org_user_id: int,
    current_worker: Worker = Depends(require_permission("can_view_clients")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_or_create_referral_code(db, org_user_id)


# ── FAQ ────────────────────────────────────────────────

@router.get("/faq", response_model=list[FaqRead])
async def get_faqs(
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_faqs(db, current_worker.org_id)


@router.post("/faq", response_model=FaqRead, status_code=201)
async def create_faq(
    data: FaqCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.create_faq(db, current_worker.org_id, data)


@router.patch("/faq/{faq_id}", response_model=FaqRead)
async def update_faq(
    faq_id: int,
    data: FaqUpdate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.update_faq(db, faq_id, current_worker.org_id, data)


@router.delete("/faq/{faq_id}", status_code=204)
async def delete_faq(
    faq_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    await extras.delete_faq(db, faq_id, current_worker.org_id)


# ── Links ──────────────────────────────────────────────

@router.get("/links", response_model=list[LinkRead])
async def get_links(
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.get_links(db, current_worker.org_id)


@router.post("/links", response_model=LinkRead, status_code=201)
async def create_link(
    data: LinkCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await extras.create_link(db, current_worker.org_id, data)


@router.delete("/links/{link_id}", status_code=204)
async def delete_link(
    link_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    await extras.delete_link(db, link_id, current_worker.org_id)





# ── Price Lists ────────────────────────────────────────

@router.get("/price-lists", response_model=list[PriceListRead])
async def get_price_lists(
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    return await pl_service.get_price_lists(db, current_worker.org_id)


@router.post("/price-lists", response_model=PriceListRead, status_code=201)
async def create_price_list(
    data: PriceListCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await pl_service.create_price_list(db, current_worker.org_id, data)


@router.delete("/price-lists/{pl_id}", status_code=204)
async def delete_price_list(
    pl_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    await pl_service.delete_price_list(db, pl_id, current_worker.org_id)


@router.get("/price-lists/{pl_id}/items", response_model=list[PriceListItemRead])
async def get_price_list_items(
    pl_id: int,
    current_worker: Worker = Depends(require_permission("can_view_products")),
    db: AsyncSession = Depends(get_db),
):
    return await pl_service.get_items(db, pl_id)


@router.post("/price-lists/{pl_id}/items", response_model=PriceListItemRead, status_code=201)
async def set_price_list_item(
    pl_id: int,
    data: PriceListItemCreate,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await pl_service.set_item_price(db, pl_id, data)


@router.delete("/price-lists/{pl_id}/items/{item_id}", status_code=204)
async def delete_price_list_item(
    pl_id: int,
    item_id: int,
    current_worker: Worker = Depends(require_permission("is_admin")),
    db: AsyncSession = Depends(get_db),
):
    await pl_service.delete_item(db, item_id, pl_id)