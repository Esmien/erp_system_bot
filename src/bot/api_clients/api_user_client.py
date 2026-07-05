from loguru import logger

from bot.api_clients.api_base_client import ApiBaseClient
from bot.schemas.user_schemas import UserRead


class ApiUserClient(ApiBaseClient):
    async def get_my_info(self, token: str) -> UserRead | None:
        user = None
        url = "/users/me/"
        headers = {"Authorization": f"Bearer {token}"}

        async with self._safe_request():
            response = await self.client.get(url=url, headers=headers)
            status_code = response.status_code

            if status_code == 200:
                raw_data = response.json()
                logger.success(f"Успешно получены данные пользователя {self.tg_id}")
                raw_data["tg_id"] = self.tg_id
                user = UserRead(**raw_data)
            else:
                logger.error(f"Ошибка при получении данных пользователя {self.tg_id}: Status Code: {status_code}")

        return user
