from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.api_clients.api_auth_client import ApiAuthClient
from bot.api_clients.api_registration_client import ApiRegistrationClient


class ApiClientMiddleware(BaseMiddleware):
    """
    Middleware для инъекции API-клиентов в хэндлеры.
    Инициализирует клиенты один раз за жизненный цикл апдейта (сообщения).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        # Aiogram сам кладет текущего пользователя в data
        user = data.get("event_from_user")

        if user:
            # Создаем инстансы клиентов.
            # Хэндлеры сразу получают ТГ ID
            data["auth_client"] = ApiAuthClient(tg_id=user.id)
            data["reg_client"] = ApiRegistrationClient()

        # Передаем управление дальше хэндлерам
        return await handler(event, data)
