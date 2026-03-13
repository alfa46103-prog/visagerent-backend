# Файл: tests/test_organizations.py
# Назначение: Тесты CRUD организаций.

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_organization(client: AsyncClient, worker_headers: dict, db_session):
    """
    Создание организации.

    Примечание: для этого теста нужен worker с is_admin правами.
    Но /organizations пока без проверки прав (для супер-админа).
    Поэтому шлём без авторизации — позже ужесточим.
    """
    response = await client.post(
        "/api/v1/organizations/",
        json={
            "name": "Test Shop",
            "slug": "test-shop",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Shop"
    assert data["slug"] == "test-shop"
    assert data["is_active"] == True
    assert "id" in data


@pytest.mark.asyncio
async def test_get_organizations(client: AsyncClient):
    """Получить список организаций (пустой)."""
    response = await client.get("/api/v1/organizations/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_and_get_organization(client: AsyncClient):
    """Создать организацию и получить её по ID."""
    # Создаём
    create_response = await client.post(
        "/api/v1/organizations/",
        json={"name": "My Shop", "slug": "my-shop"},
    )
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]

    # Получаем по ID
    get_response = await client.get(f"/api/v1/organizations/{org_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "My Shop"


@pytest.mark.asyncio
async def test_update_organization(client: AsyncClient):
    """Создать и обновить организацию."""
    # Создаём
    create_response = await client.post(
        "/api/v1/organizations/",
        json={"name": "Old Name", "slug": "old-name"},
    )
    org_id = create_response.json()["id"]

    # Обновляем
    patch_response = await client.patch(
        f"/api/v1/organizations/{org_id}",
        json={"name": "New Name"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "New Name"
    # slug не менялся
    assert patch_response.json()["slug"] == "old-name"


@pytest.mark.asyncio
async def test_delete_organization(client: AsyncClient):
    """Создать и удалить организацию."""
    # Создаём организацию без авто-создания ролей
    # Для этого напрямую через клиент
    create_response = await client.post(
        "/api/v1/organizations/",
        json={"name": "To Delete", "slug": "to-delete"},
    )
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]

    # Удаляем
    delete_response = await client.delete(f"/api/v1/organizations/{org_id}")
    assert delete_response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(f"/api/v1/organizations/{org_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_slug(client: AsyncClient):
    """Нельзя создать две организации с одинаковым slug."""
    await client.post(
        "/api/v1/organizations/",
        json={"name": "Shop 1", "slug": "same-slug"},
    )

    response = await client.post(
        "/api/v1/organizations/",
        json={"name": "Shop 2", "slug": "same-slug"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_organization_not_found(client: AsyncClient):
    """Запрос несуществующей организации — 404."""
    response = await client.get("/api/v1/organizations/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_active(client: AsyncClient):
    """Фильтрация по is_active."""
    # Создаём две организации
    await client.post(
        "/api/v1/organizations/",
        json={"name": "Active", "slug": "active", "is_active": True},
    )
    resp2 = await client.post(
        "/api/v1/organizations/",
        json={"name": "Inactive", "slug": "inactive", "is_active": False},
    )

    # Только активные
    response = await client.get("/api/v1/organizations/?is_active=true")
    data = response.json()
    assert all(org["is_active"] for org in data)

    # Только неактивные
    response = await client.get("/api/v1/organizations/?is_active=false")
    data = response.json()
    assert all(not org["is_active"] for org in data)