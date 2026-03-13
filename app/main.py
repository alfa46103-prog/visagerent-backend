# Файл: app/main.py
# Назначение: Главный файл FastAPI-приложения.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings

# Создаём экземпляр FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для мультитенантной SaaS-платформы управления Telegram-магазинами",
    version=settings.VERSION,
)

# CORS — разрешаем запросы с React-админки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры v1
app.include_router(api_router, prefix=settings.API_V1_STR)