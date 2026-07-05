from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject
from loguru import logger


class AutoAuthMiddleware(BaseMiddleware):
    """
    Мидлварь для бесшовного восстановления сессии.
    Если токен протух (удалился из Redis), мидлварь тихо сходит на бэкенд,
    получит новый и положит его в стейт ДО того, как отработает хэндлер.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        state: FSMContext | None = data.get("state")
        auth_client = data.get("auth_client")

        # Если по какой-то причине нет стейта или клиента — пропускаем
        if not state or not auth_client:
            return await handler(event, data)

        current_state = await state.get_state()

        # ВАЖНО: Если юзер находится в процессе ввода email или пароля
        # (current_state не пустой), мы не должны дергать бэкенд, чтобы не мешать.
        if current_state:
            return await handler(event, data)

        state_data = await state.get_data()

        # Магия здесь: токена нет, значит сессия истекла или это новый юзер
        if not state_data.get("access_token"):
            access_token, refresh_token = await auth_client.attempt_telegram_login()

            # Если бэкенд пустил, обновляем память FSM
            if access_token:
                logger.debug("Авторизация прошла через Middleware")
                await state.update_data(access_token=access_token, refresh_token=refresh_token)

        # Передаем управление дальше. Хэндлер (например, /me) вызовет
        # await state.get_data() и уже ГАРАНТИРОВАННО получит свежий токен!
        return await handler(event, data)
