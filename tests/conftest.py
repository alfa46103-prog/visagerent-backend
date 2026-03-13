# Файл: tests/conftest.py
# Назначение: Общие фикстуры для всех тестов.
#
# Создаёт:
#   - тестовую БД в памяти (SQLite async)
#   - тестовый клиент FastAPI (httpx.AsyncClient)
#   - сервисный токен для авторизации запросов
#
# SQLite используется для тестов потому что:
#   - не нужен запущенный PostgreSQL
#   - каждый тест получает чистую БД
#   - быстро работает
#
# Ограничение: некоторые PostgreSQL-специфичные вещи
# (ENUM, JSON-операторы) могут не работать в SQLite.
# Для полных интеграционных тестов нужен PostgreSQL (testcontainers).

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app


# ── Тестовый движок БД (SQLite in-memory) ──────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db?pragma=foreign_keys(1)"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Фикстуры ──────────────────────────────────────────
from sqlalchemy import event

#@event.listens_for(test_engine.sync_engine, "connect")
#def set_sqlite_pragma(dbapi_connection, connection_record):
#    """Включить поддержку foreign keys в SQLite (по умолчанию выключена)."""
#    cursor = dbapi_connection.cursor()
#    cursor.execute("PRAGMA foreign_keys=ON")
#    cursor.close()

    
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """
    Создаёт все таблицы перед каждым тестом
    и удаляет после. Каждый тест — чистая БД.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Тестовая сессия БД."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    """
    Тестовый HTTP-клиент.

    Подменяет зависимость get_db на тестовую сессию,
    чтобы запросы шли в тестовую БД, а не в боевую.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def service_token():
    """
    Сервисный токен для авторизации запросов от бота.
    org_id=1, type="service".
    """
    return create_access_token(
        data={"sub": "1", "type": "service", "org_id": 1}
    )


@pytest_asyncio.fixture
def service_headers(service_token):
    """Заголовки с сервисным токеном."""
    return {"Authorization": f"Bearer {service_token}"}


@pytest_asyncio.fixture
def worker_token():
    """
    Токен сотрудника-админа для тестов через админские эндпоинты.
    worker_id=1, type="worker".
    """
    return create_access_token(
        data={"sub": "1", "type": "worker"}
    )


@pytest_asyncio.fixture
def worker_headers(worker_token):
    """Заголовки с токеном сотрудника."""
    return {"Authorization": f"Bearer {worker_token}"}