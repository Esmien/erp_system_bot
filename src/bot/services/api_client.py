import logging

import httpx

from bot.core.config import settings

logger = logging.getLogger(__name__)

# Создаем константу локально для удобства использования
API_BASE_URL = settings.api.API_BASE_URL


async def attempt_telegram_login(tg_id: int) -> str | None:
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
                data = response.json()
                return data.get("access_token")

            # Если 401 Unauthorized или 404 (юзера нет/не привязан)
            return None

        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения с бэкендом: {e}")
            return None


async def link_telegram_account(tg_id: int, email: str, password: str) -> str | None:
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
                data = response.json()
                return data.get("access_token")  # Сразу забираем токен из ответа

            logger.warning(f"Ошибка привязки аккаунта: {response.text}")
            return None

        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения с бэкендом при привязке: {e}")
            return None


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
                return True

            logger.warning(f"Ошибка отвязки аккаунта: {response.text}")
            return False

        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения с бэкендом при отвязке: {e}")
            return False
