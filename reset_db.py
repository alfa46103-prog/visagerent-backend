#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для полной очистки схемы public в PostgreSQL.
ВНИМАНИЕ: УДАЛЯЕТ ВСЕ ТАБЛИЦЫ, ПРЕДСТАВЛЕНИЯ, ТИПЫ И ДРУГИЕ ОБЪЕКТЫ В ПУБЛИЧНОЙ СХЕМЕ!
Используйте только на пустой или тестовой базе данных.
"""

import asyncio
import asyncpg
from app.core.config import settings  # используем настройки из проекта


async def reset_schema():
    """
    Подключается к базе данных и выполняет команды:
    - DROP SCHEMA public CASCADE
    - CREATE SCHEMA public
    - GRANT ALL ON SCHEMA public TO postgres
    - GRANT ALL ON SCHEMA public TO public
    """
    # Извлекаем параметры подключения из DATABASE_URL
    db_url = str(settings.DATABASE_URL)
    # asyncpg требует строку без +asyncpg, поэтому убираем диалект
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = 'postgresql://' + db_url[len('postgresql+asyncpg://'):]
    elif db_url.startswith('postgresql://'):
        pass  # уже нормально
    else:
        raise ValueError("Неподдерживаемый формат DATABASE_URL")

    print(f"Подключаюсь к базе по URL: {db_url}")

    # Устанавливаем соединение
    conn = await asyncpg.connect(db_url)

    try:
        # Отключаем всех других клиентов (опционально, но может помочь избежать блокировок)
        # await conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();")

        print("Удаляем схему public...")
        await conn.execute("DROP SCHEMA public CASCADE;")

        print("Создаём схему public заново...")
        await conn.execute("CREATE SCHEMA public;")

        print("Восстанавливаем права доступа...")
        await conn.execute("GRANT ALL ON SCHEMA public TO postgres;")
        await conn.execute("GRANT ALL ON SCHEMA public TO public;")

        print("✅ Схема public успешно очищена.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(reset_schema())