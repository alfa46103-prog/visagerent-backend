# Файл: tests/test_bot_api.py
# Назначение: Тесты эндпоинтов для бота (/bot/*).

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, service_headers: dict, db_session):
    """Регистрация покупателя через бота."""
    # Сначала нужна организация с id=1
    from app.models.organization import Organization
    org = Organization(id=1, name="Test", slug="test")
    db_session.add(org)
    await db_session.commit()

    response = await client.post(
        "/api/v1/bot/register-user",
        json={
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
        },
        headers=service_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] == True
    assert "org_user_id" in data


@pytest.mark.asyncio
async def test_register_user_twice(client: AsyncClient, service_headers: dict, db_session):
    """Повторная регистрация не создаёт дубликат."""
    from app.models.organization import Organization
    org = Organization(id=1, name="Test", slug="test")
    db_session.add(org)
    await db_session.commit()

    # Первый раз
    resp1 = await client.post(
        "/api/v1/bot/register-user",
        json={"telegram_id": 111111, "username": "user1"},
        headers=service_headers,
    )
    user_id_1 = resp1.json()["org_user_id"]

    # Второй раз — тот же telegram_id
    resp2 = await client.post(
        "/api/v1/bot/register-user",
        json={"telegram_id": 111111, "username": "user1"},
        headers=service_headers,
    )
    user_id_2 = resp2.json()["org_user_id"]

    # Один и тот же пользователь
    assert user_id_1 == user_id_2


@pytest.mark.asyncio
async def test_get_points(client: AsyncClient, service_headers: dict, db_session):
    """Список точек организации."""
    from app.models.organization import Organization
    from app.models.point import Point

    org = Organization(id=1, name="Test", slug="test")
    db_session.add(org)
    await db_session.flush()

    point = Point(org_id=1, name="Main Point", address="ул. Центральная, 1")
    db_session.add(point)
    await db_session.commit()

    response = await client.get(
        "/api/v1/bot/points",
        headers=service_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Main Point"


@pytest.mark.asyncio
async def test_empty_cart(client: AsyncClient, service_headers: dict, db_session):
    """Корзина нового пользователя пуста."""
    from app.models.organization import Organization
    org = Organization(id=1, name="Test", slug="test")
    db_session.add(org)
    await db_session.commit()

    # Регистрируем пользователя
    await client.post(
        "/api/v1/bot/register-user",
        json={"telegram_id": 555555},
        headers=service_headers,
    )

    response = await client.get(
        "/api/v1/bot/cart?telegram_id=555555",
        headers=service_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_faq_empty(client: AsyncClient, service_headers: dict, db_session):
    """FAQ пустой если ничего не создано."""
    from app.models.organization import Organization
    org = Organization(id=1, name="Test", slug="test")
    db_session.add(org)
    await db_session.commit()

    response = await client.get(
        "/api/v1/bot/faq",
        headers=service_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_worker_not_found(client: AsyncClient, service_headers: dict, db_session):
    """Запрос профиля несуществующего сотрудника."""
    from app.models.organization import Organization
    org = Organization(id=1, name="Test", slug="test")
    db_session.add(org)
    await db_session.commit()

    response = await client.get(
        "/api/v1/bot/worker/me?telegram_id=999999",
        headers=service_headers,
    )
    data = response.json()
    assert data.get("error") == True


@pytest.mark.asyncio
async def test_no_service_token(client: AsyncClient):
    """Запрос без сервисного токена — 401/403."""
    response = await client.get("/api/v1/bot/points")
    assert response.status_code in [401, 403]