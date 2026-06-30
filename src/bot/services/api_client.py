import httpx
from httpx import Response
from loguru import logger

from bot.core.config import settings
from bot.core.redis import redis_client

# Создаем константу локально для удобства использования
API_BASE_URL = settings.api.API_BASE_URL


def _get_tokens(response: Response) -> tuple[str, str] | None:
    data = response.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    return access_token, refresh_token


async def attempt_telegram_login(tg_id: int) -> tuple[str, str] | tuple[None, None] | None:
    """
    Отправляет запрос на бэкенд для тихой аутентификации

    Args:
        tg_id: TelegramID пользователя

    Returns:
        JWT access токен при успехе, иначе None
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.post(url="/auth/telegram/login/", json={"tg_id": tg_id})
            if response.status_code == 200:
                access_token, refresh_token = _get_tokens(response=response)
                logger.debug(f"ACCESS: {access_token[:-10]}, REFRESH: {refresh_token[:-10]} для User: {tg_id}")
                return access_token, refresh_token

            # Если 401 Unauthorized или 404 (юзера нет/не привязан)
            return None, None

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом: {e}")
            return None, None


async def link_telegram_account(tg_id: int, email: str, password: str) -> tuple[str, str] | tuple[None, None]:
    """
    Отправляет креды на бэкенд для привязки

    Args:
        tg_id: TelegramID для привязки к учетке
        email: почта пользователя ERP
        password: пароль пользователя ERP

    Returns:
        JWT access токен при успехе, иначе None
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            payload = {"username": email, "password": password, "tg_id": tg_id}
            response = await client.post(url="/auth/telegram/link/", json=payload)

            if response.status_code == 200:
                access_token, refresh_token = _get_tokens(response=response)
                return access_token, refresh_token

            logger.warning(f"Ошибка привязки аккаунта: {response.text}")
            return None, None

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при привязке: {e}")
            return None, None


async def unlink_telegram_account(tg_id: int) -> bool:
    """
    Логаут: отвязывает Telegram ID на стороне бэкенда
    Требует JWT-токен текущего пользователя.

    Args:
        tg_id: TelegramID пользователя, выполняющего logout

    Returns:
        True, если все в порядке, False, если бэкенд вернул ошибку
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            # Просто передаем на бэк секретный ключ в заголовке и TGID пользователя
            headers = {"x-bot-secret-token": settings.webhook.WEBHOOK_SECRET}
            payload = {"tg_id": tg_id}

            response = await client.post(url="/auth/telegram/unlink/", json=payload, headers=headers)

            if response.status_code == 200:
                await redis_client.delete(f"backend:jwt:access:{tg_id}", f"backend:jwt:refresh:{tg_id}")
                return True

            logger.warning(f"Ошибка отвязки аккаунта: {response.text}")
            return False

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при отвязке: {e}")
            return False


async def get_registration_code(token: str) -> tuple[int | None, str | None]:
    """
    Получает код для регистрации. Работает только для админов.

    Args:
        token: JWT токен пользователя, который генерирует

    Returns:
        Кортеж, состоящий из полученного статус-кода от бэкенда и кода регистрации.
        Если бэк недоступен, то статус-код None
        Если бэк не ответил 201 OK, код регистрации None
    """
    url = "/auth/generate-register-code/"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.post(url=url, headers=headers)
            status_code = response.status_code
            register_code = None

            if status_code == 201:
                data = response.json()
                register_code = data.get("register_code")
                logger.success(f"Код регистрации {register_code} успешно сгенерирован")
            else:
                logger.error(f"Неожиданный ответ от бэкенда при генерации кода: {status_code}")

            return status_code, register_code
        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при отвязке: {e}")
            return None, None
