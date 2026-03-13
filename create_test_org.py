#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для создания тестовой организации VisageRENT.
Запускать после активации виртуального окружения.
"""

import asyncio
from datetime import datetime
from app.core.database import AsyncSessionLocal
from app.models.organization import Organization


async def create_org():
    """Создаёт тестовую организацию в базе данных."""
    async with AsyncSessionLocal() as session:
        # Проверим, нет ли уже такой организации
        from sqlalchemy import select
        result = await session.execute(
            select(Organization).where(Organization.slug == "visagerent")
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Организация уже существует: {existing.name} (id={existing.id})")
            return existing.id

        # Создаём новую организацию
        org = Organization(
            name="VisageRENT",
            slug="visagerent",
            settings={
                "currency": "RUB",
                "timezone": "Europe/Moscow",
                "contacts": {
                    "email": "info@visagerent.ru",
                    "phone": "+7 (999) 123-45-67"
                }
            },
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(org)
        await session.commit()
        await session.refresh(org)
        print(f"✅ Организация создана: {org.name} (id={org.id})")
        return org.id


if __name__ == "__main__":
    asyncio.run(create_org())