from dataclasses import dataclass

from loguru import logger

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_registration_client import ApiRegistrationClient
from bot.api_clients.api_user_client import ApiUserClient
from bot.schemas.user_schemas import UserRegister


@dataclass
class RegistrationResult:
    """Объект результата процесса регистрации и привязки аккаунта"""

    is_success: bool
    is_linked: bool = False
    status_code: int | None = None
    error_msg: str | None = None
    role: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None


class RegistrationService:
    def __init__(
        self,
        reg_client: ApiRegistrationClient,
        auth_client: ApiAuthClient,
        user_client: ApiUserClient,
    ):
        self.reg_client = reg_client
        self.auth_client = auth_client
        self.user_client = user_client

    async def check_invite_code(self, code: str) -> bool:
        """Делегируем проверку кода сервису для инкапсуляции"""
        return await self.reg_client.check_registration_code(code=code)

    async def register_and_link(self, user_payload: dict) -> RegistrationResult:
        """
        Единая бизнес-транзакция:
        1. Создание пользователя в ERP.
        2. Привязка его Telegram ID.
        3. Получение роли для построения интерфейса.
        """
        # Отсекаем технические данные FSM (оставляем Pydantic чистым)
        user_payload.pop("last_bot_msg_id", None)

        try:
            user = UserRegister(**user_payload)
        except ValueError as e:
            logger.error(f"Ошибка сборки модели UserRegister: {e}")
            return RegistrationResult(is_success=False, status_code=422, error_msg="Внутренняя ошибка валидации")

        status_code, response_data = await self.reg_client.register_new_user(user)

        if status_code == 201:
            # Регистрация успешна. Немедленно склеиваем аккаунты
            access_token, refresh_token = await self.auth_client.link_telegram_account(
                email=user.email, password=user.password
            )

            if access_token:
                # Токен получен, идем за профилем, чтобы узнать роль
                my_info = await self.user_client.get_my_info(token=access_token)
                role = my_info.role.name.lower() if my_info else None

                return RegistrationResult(
                    is_success=True,
                    is_linked=True,
                    status_code=status_code,
                    role=role,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )

            # Зарегистрировались, но привязка ТГ отвалилась
            return RegistrationResult(is_success=True, is_linked=False, status_code=status_code)

        elif status_code == 400:
            error_msg = response_data.get("detail") if response_data else "Ошибка валидации бэкенда"
            return RegistrationResult(is_success=False, status_code=status_code, error_msg=error_msg)

        else:
            logger.error(f"Неизвестная ошибка при регистрации: {status_code} - {response_data}")
            return RegistrationResult(is_success=False, status_code=status_code)
