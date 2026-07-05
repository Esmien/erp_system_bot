from loguru import logger

from bot.api_clients.api_base_client import ApiBaseClient
from bot.schemas.user_schemas import RoleForCodeDTO, UserRegister


class ApiRegistrationClient(ApiBaseClient):
    async def get_roles(self, token: str) -> list[dict] | None:
        url = "/users/roles/"
        headers = {"Authorization": f"Bearer {token}"}

        async with self._safe_request():
            response = await self.client.get(url=url, headers=headers)
            status_code = response.status_code

            if status_code == 200:
                roles = response.json()

                logger.success(f"Успешно получен список ролей: {roles}")
                return roles

            logger.error(f"Неожиданный ответ от бэкенда при получении списка ролей: {status_code}")

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

        async with self._safe_request():
            response = await self.client.post(url=url, headers=headers, json=payload)
            status_code = response.status_code

            if status_code == 201:
                data = response.json()
                register_code = data.get("register_code")

                logger.success(f"Код регистрации {register_code} успешно сгенерирован")
                return status_code, register_code
            else:
                logger.error(f"Неожиданный ответ от бэкенда при генерации кода: {status_code}")

        return None, None

    async def check_registration_code(self, code: str) -> bool:
        """
        Быстрая проверка валидности кода регистрации

        Args:
            code: код для проверки

        Returns:
            True, если валиден, False, если нет
        """
        # Инициализируем до запроса, чтобы при ошибке вернуть нормальный результат
        is_code_valid = False

        async with self._safe_request():
            response = await self.client.get(url=f"/register_code/{code}/validate/")
            is_code_valid = response.status_code == 200

        return is_code_valid

    async def register_new_user(self, user_data: UserRegister) -> tuple[int | None, dict | None]:
        """Отправка данных на регистрацию"""
        status_code, data = None, None

        async with self._safe_request():
            response = await self.client.post(url="/auth/register/", json=user_data.model_dump(exclude_unset=True))
            status_code = response.status_code
            data = response.json()

        return status_code, data
