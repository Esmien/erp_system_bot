import httpx
from httpx import Response
from loguru import logger

from bot.core.config import settings
from bot.core.http_client import http_manager
from bot.core.redis import redis_client


class ApiAuthClient:
    def __init__(self, tg_id: int):
        self.tg_id = tg_id
        self.client = http_manager.client

    @staticmethod
    def _get_tokens(response: Response) -> tuple[str, str]:
        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        return access_token, refresh_token

    async def attempt_telegram_login(self) -> tuple[str, str] | tuple[None, None] | None:
        """
        Отправляет запрос на бэкенд для тихой аутентификации

        Returns:
            JWT access токен при успехе, иначе None
        """
        try:
            response = await self.client.post(url="/telegram/login/", json={"tg_id": self.tg_id})

            if response.status_code == 200:
                access_token, refresh_token = self._get_tokens(response=response)
                logger.debug(f"ACCESS: {access_token[:-10]}, REFRESH: {refresh_token[:-10]} для User: {self.tg_id}")
                return access_token, refresh_token

            # Если 401 Unauthorized или 404 (юзера нет/не привязан)
            return None, None

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом: {e}")
            return None, None

    async def link_telegram_account(self, email: str, password: str) -> tuple[str, str] | tuple[None, None]:
        """
        Отправляет креды на бэкенд для привязки

        Args:
            email: почта пользователя ERP
            password: пароль пользователя ERP

        Returns:
            JWT access токен при успехе, иначе None
        """
        try:
            payload = {"username": email, "password": password, "tg_id": self.tg_id}
            response = await self.client.post(url="/telegram/link/", json=payload)

            if response.status_code == 200:
                access_token, refresh_token = self._get_tokens(response=response)
                return access_token, refresh_token

            logger.warning(f"Ошибка привязки аккаунта: {response.text}")
            return None, None

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при привязке: {e}")
            return None, None

    async def unlink_telegram_account(self) -> bool:
        """
        Логаут: отвязывает Telegram ID на стороне бэкенда
        Требует JWT-токен текущего пользователя.

        Returns:
            True, если все в порядке, False, если бэкенд вернул ошибку
        """
        try:
            # Просто передаем на бэк секретный ключ в заголовке и TGID пользователя
            headers = {"x-bot-secret-token": settings.webhook.WEBHOOK_SECRET}
            payload = {"tg_id": self.tg_id}

            response = await self.client.post(url="/telegram/unlink/", json=payload, headers=headers)

            if response.status_code == 200:
                await redis_client.delete(f"backend:jwt:access:{self.tg_id}", f"backend:jwt:refresh:{self.tg_id}")
                return True

            logger.warning(f"Ошибка отвязки аккаунта: {response.text}")
            return False

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при отвязке: {e}")
            return False
