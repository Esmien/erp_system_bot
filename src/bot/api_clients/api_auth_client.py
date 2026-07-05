from httpx import Response
from loguru import logger

from bot.api_clients.api_base_client import ApiBaseClient
from bot.core.config import settings
from bot.core.redis import redis_client
from bot.schemas.user_schemas import UserLogin


class ApiAuthClient(ApiBaseClient):
    @staticmethod
    def _get_tokens(response: Response) -> tuple[str, str]:
        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        return access_token, refresh_token

    async def attempt_telegram_login(self) -> tuple[str | None, str | None]:
        """
        Отправляет запрос на бэкенд для тихой аутентификации

        Returns:
            JWT access токен при успехе, иначе None
        """
        access_token, refresh_token = None, None

        async with self._safe_request():
            response = await self.client.post(url="/telegram/login/", json={"tg_id": self.tg_id})

            if response.status_code == 200:
                access_token, refresh_token = self._get_tokens(response=response)
                logger.debug(f"ACCESS: {access_token[:-10]}, REFRESH: {refresh_token[:-10]} для User: {self.tg_id}")

        return access_token, refresh_token

    async def link_telegram_account(self, email: str, password: str) -> tuple[str | None, str | None]:
        """
        Отправляет креды на бэкенд для привязки

        Args:
            email: почта пользователя ERP
            password: пароль пользователя ERP

        Returns:
            JWT access токен при успехе, иначе None
        """
        access_token, refresh_token = None, None

        async with self._safe_request():
            user = UserLogin(username=email, password=password, tg_id=self.tg_id)
            payload = user.model_dump()

            response = await self.client.post(url="/telegram/link/", json=payload)

            if response.status_code == 200:
                access_token, refresh_token = self._get_tokens(response=response)
            else:
                logger.warning(f"Ошибка привязки аккаунта: {response.text}")

        return access_token, refresh_token

    async def unlink_telegram_account(self) -> bool:
        """
        Логаут: отвязывает Telegram ID на стороне бэкенда
        Требует JWT-токен текущего пользователя.

        Returns:
            True, если все в порядке, False, если бэкенд вернул ошибку
        """
        async with self._safe_request():
            # Просто передаем на бэк секретный ключ в заголовке и TGID пользователя
            headers = {"x-bot-secret-token": settings.webhook.WEBHOOK_SECRET}
            payload = {"tg_id": self.tg_id}

            response = await self.client.post(url="/telegram/unlink/", json=payload, headers=headers)

            if response.status_code == 200:
                await redis_client.delete(f"backend:jwt:access:{self.tg_id}", f"backend:jwt:refresh:{self.tg_id}")
                return True

            logger.warning(f"Ошибка отвязки аккаунта: {response.text}")

        return False
