from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI, HTTPException, Request, status
from loguru import logger

from bot.core.config import settings
from bot.core.http_client import http_manager
from bot.core.logger import setup_logger
from bot.core.redis import close_redis, redis_client, storage
from bot.handlers.admin_handler import router as admin_router
from bot.handlers.auth_handler import router as auth_router
from bot.handlers.base_handler import router as base_router
from bot.handlers.registration_handler import router as register_router
from bot.handlers.user_handler import router as user_router
from bot.middlewares.api_clients_middleware import ApiClientMiddleware
from bot.middlewares.auth_middleware import AutoAuthMiddleware

# Инициализация aiogram
bot = Bot(token=settings.bot.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)
# Регистрируем мидлварь для всех обновлений
dp.update.outer_middleware(ApiClientMiddleware())
dp.update.outer_middleware(AutoAuthMiddleware())

# Блок с регистрацией роутеров (хэндлеров)
dp.include_router(router=base_router)
dp.include_router(router=auth_router)
dp.include_router(router=admin_router)
dp.include_router(router=register_router)
dp.include_router(router=user_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл FastAPI-приложения: старт и остановка"""
    setup_logger()

    # Запускаем HTTP-клиент
    http_manager.start()

    # Собираем полный URL для вебхука
    webhook_url = f"{settings.webhook.WEBHOOK_HOST}{settings.webhook.WEBHOOK_PATH}"

    logger.info(f"Устанавливаем вебхук на {webhook_url}")
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook.WEBHOOK_SECRET,
        drop_pending_updates=True,  # Игнорируем старые сообщения, пока бот лежал
        allowed_updates=dp.resolve_used_update_types(),
    )
    logger.success("Вебхук установлен")
    await redis_client.set(settings.redis.KEY_OF_SYSTEM_TOKEN, settings.webhook.WEBHOOK_SECRET)
    logger.success("Системный секрет опубликован в Redis")

    yield

    logger.info("Удаляем вебхук и закрываем сессию бота")
    await bot.delete_webhook()
    await bot.session.close()
    await close_redis()

    # Закрываем HTTP клиент
    await http_manager.stop()

    logger.success("Сервис успешно остановлен")


app = FastAPI(lifespan=lifespan)


@app.post(
    path=settings.webhook.WEBHOOK_PATH,
    status_code=status.HTTP_200_OK,
    summary="Эндпоинт для получения обновлений из ТГ",
)
async def bot_webhook(request: Request):
    """Эндпоинт, на который Telegram присылает обновления"""
    # Проверка секретного токена для защиты от левых запросов
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_token != settings.webhook.WEBHOOK_SECRET:
        logger.warning("Получен запрос с неверным секретным токеном!")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Распаковываем JSON от Telegram
    update_data = await request.json()
    telegram_update = types.Update(**update_data)

    # Скармливаем апдейт диспетчеру aiogram
    await dp.feed_update(bot=bot, update=telegram_update)

    return {"status": "ok"}


@app.get("/healthcheck/")
async def healthcheck():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app=app, host=settings.bot.BOT_HOST, port=settings.bot.BOT_PORT)
