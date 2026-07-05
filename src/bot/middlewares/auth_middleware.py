import base64
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject
from loguru import logger


def is_token_expired(token: str) -> bool:
    """Декодирует JWT и проверяет срок его жизни (exp) без сторонних библиотек"""
    try:
        # JWT состоит из 3 частей: header.payload.signature. Нам нужен payload.
        payload_b64 = token.split(".")[1]
        # Добавляем паддинг, так как Python строго относится к длине base64 строки
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)

        payload = json.loads(base64.b64decode(payload_b64).decode("utf-8"))

        # Проверяем, истекает ли токен в ближайшие 10 секунд (даем запас на время полета запроса)
        return payload.get("exp", 0) < time.time() + 10
    except Exception as e:
        logger.warning(f"Не удалось распарсить JWT в Middleware: {e}")
        return True  # Если не смогли прочитать, считаем протухшим от греха подальше


class AutoAuthMiddleware(BaseMiddleware):
    """
    Мидлварь для бесшовного восстановления сессии с проверкой срока жизни JWT.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        state: FSMContext | None = data.get("state")
        auth_client = data.get("auth_client")

        if not state or not auth_client:
            return await handler(event, data)

        current_state = await state.get_state()

        # Не мешаем пользователю, если он в процессе ввода email/пароля
        if current_state:
            return await handler(event, data)

        state_data = await state.get_data()
        access_token = state_data.get("access_token")

        # МАГИЯ ЗДЕСЬ: Проверяем, что токен не только есть, но и жив
        if access_token and is_token_expired(access_token):
            logger.info("Access токен протух. Требуется бесшовное обновление.")
            access_token = None  # Обнуляем, чтобы форсировать логин

        if not access_token:
            new_access_token, refresh_token = await auth_client.attempt_telegram_login()

            if new_access_token:
                logger.success("Успешное бесшовное обновление токенов через Middleware")
                await state.update_data(access_token=new_access_token, refresh_token=refresh_token)
            elif state_data.get("access_token"):
                # Токен протух, мы сходили на бэк, но он нас послал (например, юзера забанили в ERP).
                # Жестко зачищаем память, чтобы превратить его в Гостя.
                logger.warning("Бэкенд отказал в обновлении токена. Очищаем сессию.")
                await state.clear()

        return await handler(event, data)
