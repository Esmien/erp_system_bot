import httpx
from loguru import logger

from bot.core.http_client import http_manager
from bot.schemas.user_schemas import RoleForCodeDTO, UserRegister


class ApiRegistrationClient:
    def __init__(self):
        self.client = http_manager.client

    async def get_roles(self, token: str) -> list[dict] | None:
        url = "/users/roles/"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await self.client.get(url=url, headers=headers)
            status_code = response.status_code

            if status_code == 200:
                roles = response.json()
                logger.success(f"Успешно получен список ролей: {roles}")
                return roles
            else:
                logger.error(f"Неожиданный ответ от бэкенда при получении списка ролей: {status_code}")
                return None

        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при получении ролей: {e}")
            return None

    async def get_registration_code(self, token: str, role_name: RoleForCodeDTO) -> tuple[int | None, str | None]:
        """
        Получает код для регистрации. Работает только для админов.

        Args:
            token: JWT токен пользователя, который генерирует
            role_name: название роли для кода

        Returns:
            Кортеж, состоящий из полученного статус-кода от бэкенда и кода регистрации.
            Если бэк недоступен, то статус-код None
            Если бэк не ответил 201 OK, код регистрации None
        """
        url = "/register_code/generate/"
        headers = {"Authorization": f"Bearer {token}"}
        payload = role_name.model_dump()

        try:
            response = await self.client.post(url=url, headers=headers, json=payload)
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

    async def check_registration_code(self, code) -> bool:
        """
        Быстрая проверка валидности кода регистрации

        Args:
            code: код для проверки

        Returns:
            True, если валиден, False, если нет
        """
        try:
            response = await self.client.get(url=f"/register_code/{code}/validate/")
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.exception(f"Ошибка проверки кода: {e}")
            return False

    async def register_new_user(self, user_data: UserRegister) -> tuple[int | None, dict | None]:
        """Отправка данных на регистрацию"""
        try:
            response = await self.client.post(url="/auth/register/", json=user_data.model_dump(exclude_unset=True))
            return response.status_code, response.json()
        except httpx.RequestError as e:
            logger.exception(f"Ошибка соединения с бэкендом при регистрации: {e}")
            return None, None
