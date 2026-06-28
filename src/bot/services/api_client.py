import logging

import httpx

from bot.core.config import settings

logger = logging.getLogger(__name__)

# Заглушка, если урла бэкенда пока нет в settings
API_BASE_URL = settings.api.API_BASE_URL


async def attempt_telegram_login(tg_id: int) -> str | None:
    """
    Стучится в бэкенд для тихой авторизации по Telegram ID.
    Возвращает access_token при успехе, иначе None.
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.post(url="/auth/telegram/login/", json={"tg_id": tg_id})
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")

            # Если 401 Unauthorized или 404 (юзера нет/не привязан)
            return None

        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения с бэкендом: {e}")
            return None
