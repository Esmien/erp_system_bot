from contextlib import asynccontextmanager

import httpx
from loguru import logger

from bot.core.http_client import http_manager


class ApiBaseClient:
    """
    Базовый класс для всех API-клиентов бота.
    Инкапсулирует логику отправки запросов, обработку сетевых ошибок и работу с сессией.
    """

    def __init__(self, tg_id: int):
        self.tg_id = tg_id

    @property
    def client(self) -> httpx.AsyncClient:
        # Используем property, чтобы всегда гарантированно получать инициализированный клиент
        return http_manager.client

    @asynccontextmanager
    async def _safe_request(self):
        """
        Магический контекстный менеджер.
        Ловит httpx.RequestError, пишет в лог и позволяет коду безопасно идти дальше.
        """
        try:
            yield
        except httpx.RequestError as e:
            logger.exception(f"Сетевая ошибка при обращении к API: {e}")
