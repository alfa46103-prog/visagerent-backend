# Файл: app/core/config.py
# Назначение: Единый конфиг приложения.
# Загружает переменные из .env через pydantic-settings.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Все переменные загружаются из .env."""

    # Общие
    PROJECT_NAME: str = "VisageRENT API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # БД — строка подключения (postgresql+asyncpg://...)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/visagerent"

    # Безопасность
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней

    # CORS — список разрешённых origins для React-админки
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Список Telegram ID супер-админов (через запятую в .env)
    SUPER_ADMIN_IDS: list[int] = []
    
# Единственный экземпляр настроек
settings = Settings()