from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.core.config import settings

# Создаем объекты СРАЗУ. Сетевого подключения прямо здесь не произойдет,
# мы просто инициализируем пул соединений и хранилище.
redis_client = Redis.from_url(url=settings.redis.redis_url, decode_responses=True)
redis_client_config = Redis.from_url(url=settings.redis.redis_config_url, decode_responses=True)

# Передаем клиент в хранилище aiogram
storage = RedisStorage(redis=redis_client, key_builder=DefaultKeyBuilder(with_destiny=True))


def get_redis() -> Redis:
    """Провайдер для Dependency Injection в FastAPI"""
    return redis_client


async def close_redis() -> None:
    """Корректно закрываем пулы при остановке приложения"""
    await redis_client.aclose()
    await redis_client_config.aclose()
    await storage.close()
