# Файл: app/core/security.py
# Назначение: функции для создания и проверки JWT-токенов,
# а также хеширование/проверка паролей.

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# ВАЖНО:
# Используем именно JWTError из python-jose.
# Раньше ловился jwt.PyJWTError, это исключение из другой библиотеки.
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Контекст для хеширования паролей.
# Пока пароли у тебя не главный механизм входа, но оставляем на будущее.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Базовые JWT-настройки из конфигурации.
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Создаёт JWT-токен.

    Что кладём в токен:
    - любые данные из аргумента data
    - обязательный exp (время истечения)

    Примеры payload:
    - {"sub": "1", "type": "global"}
    - {"sub": "15", "type": "org"}
    - {"sub": "2", "type": "service", "org_id": 3}
    """
    # Копируем payload, чтобы не мутировать исходный словарь.
    to_encode = data.copy()

    # Если срок жизни передали явно — используем его.
    # Иначе берём дефолт из настроек.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Добавляем время истечения в payload.
    to_encode.update({"exp": expire})

    # Кодируем JWT.
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Проверяет JWT-токен.

    Возвращает:
    - payload (dict), если токен валиден
    - None, если токен невалидный / просроченный / повреждённый
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Любая ошибка декодирования или истечения токена
        # трактуется как невалидный токен.
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие обычного пароля и его хеша.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Хеширует пароль.
    """
    return pwd_context.hash(password)