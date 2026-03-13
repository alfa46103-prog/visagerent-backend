# Файл: app/api/v1/__init__.py

from fastapi import APIRouter

from app.api.v1.endpoints import (
    organizations, health, auth, workers,
    categories, products, points, stock,
    cart, orders, loyalty,
    notifications, audit, finance, extras, delivery,
    bot_api,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(workers.router, prefix="/workers", tags=["workers"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(points.router, prefix="/points", tags=["points"])
api_router.include_router(stock.router, prefix="/stock", tags=["stock"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(extras.router, tags=["extras"])
api_router.include_router(delivery.router, prefix="/delivery", tags=["delivery"])
api_router.include_router(bot_api.router, prefix="/bot", tags=["bot"])