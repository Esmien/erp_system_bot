import httpx
from loguru import logger

from bot.core.http_client import http_manager


class ApiRegistrationClient:
    def __init__(self):
        self.client = http_manager.client

    async def get_registration_code(self, token: str) -> tuple[int | None, str | None]:
        """
        Получает код для регистрации. Работает только для админов.

        Args:
            token: JWT токен пользователя, который генерирует

        Returns:
            Кортеж, состоящий из полученного статус-кода от бэкенда и кода регистрации.
            Если бэк недоступен, то статус-код None
            Если бэк не ответил 201 OK, код регистрации None
        """
        url = "/register_code/generate/"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await self.client.post(url=url, headers=headers)
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
            logger.exception(f"Ошибка соединения с бэкендом при генерации кода: {e}")
            return None, None
