# Файл: tests/test_health.py
# Назначение: Тест что API вообще работает.

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Проверяем что /health возвращает 200 OK."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}