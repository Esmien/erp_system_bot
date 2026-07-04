import httpx
from loguru import logger

from bot.core.config import settings


class HttpClientManager:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    def start(self):
        """Инициализирует HTTP-клиент (вызывать при старте)"""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=settings.api.API_BASE_URL)
            logger.info("HTTP клиент успешно инициализирован.")

    async def stop(self):
        """Закрывает сессию HTTP-клиента (вызывать при остановке)"""
        if self._client:
            await self._client.aclose()
            logger.info("HTTP клиент успешно закрыт.")

    @property
    def client(self) -> httpx.AsyncClient:
        """Свойство для получения инстанса клиента"""
        if self._client is None:
            raise RuntimeError("HTTP клиент не инициализирован. Проверьте lifespan.")
        return self._client


# Создаем глобальный инстанс менеджера
http_manager = HttpClientManager()
