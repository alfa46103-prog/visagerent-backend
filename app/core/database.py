# Файл: app/core/database.py
# Назначение: Настройка асинхронного подключения к PostgreSQL через SQLAlchemy.
# Создаёт движок, фабрику сессий и базовый класс для моделей.
# Также предоставляет зависимость get_db для получения сессии в эндпоинтах.

from typing import AsyncGenerator  # для аннотации типа генератора
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# 1. Создаём асинхронный движок SQLAlchemy
#    - echo=True выводит SQL-запросы в консоль (удобно для разработки)
#    - future=True использует новейшее API SQLAlchemy 2.0
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
)

# 2. Фабрика асинхронных сессий
#    - expire_on_commit=False предотвращает устаревание объектов после коммита
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 3. Базовый класс для всех моделей SQLAlchemy
#    От него будут наследоваться все таблицы.
Base = declarative_base()


# 4. Функция-генератор для получения сессии БД в эндпоинтах FastAPI
#    Используется как зависимость (Depends).
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость, которая открывает сессию БД, передаёт её в обработчик,
    а после завершения запроса автоматически закрывает.
    Возвращает асинхронный генератор, который выдаёт сессию.
    """
    async with AsyncSessionLocal() as session:
        yield session  # сессия будет доступна во время запроса