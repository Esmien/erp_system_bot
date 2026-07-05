from dataclasses import dataclass

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_user_client import ApiUserClient


@dataclass
class StartAuthResult:
    """Объект, который сервис возвращает хэндлеру"""

    is_auth: bool
    is_new_login: bool = False
    role: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None


class AuthService:
    """
    Сервис бизнес-логики для процессов авторизации.
    Ничего не знает про Telegram (сообщения, клавиатуры), работает только с данными.
    """

    def __init__(self, auth_client: ApiAuthClient, user_client: ApiUserClient):
        self.auth_client = auth_client
        self.user_client = user_client

    async def resolve_start_auth(self, access_token: str | None, current_role: str | None) -> StartAuthResult:
        """
        Определяет статус пользователя (Уже вошел / Тихий логин / Гость)
        и подтягивает недостающие данные (роль, новые токены).
        """
        # Сценарий 1: Пользователь уже имеет активную сессию
        if access_token:
            role = current_role
            # Если токен есть, а роли нет (например, старая сессия) - идем на бэк
            if not role:
                my_info = await self.user_client.get_my_info(token=access_token)
                role = my_info.role.name.lower() if my_info else None

            return StartAuthResult(is_auth=True, role=role)

        # Сценарий 2: Память пуста, пробуем тихий логин
        new_access, new_refresh = await self.auth_client.attempt_telegram_login()
        if new_access:
            my_info = await self.user_client.get_my_info(token=new_access)
            role = my_info.role.name.lower() if my_info else None

            return StartAuthResult(
                is_auth=True, is_new_login=True, role=role, access_token=new_access, refresh_token=new_refresh
            )

        # Сценарий 3: Полный гость
        return StartAuthResult(is_auth=False)
