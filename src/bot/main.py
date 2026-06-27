import uvicorn
from fastapi import FastAPI

from bot.core.config import settings

app = FastAPI()


@app.get("/healthcheck/")
async def healthcheck():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app="bot.main:app", host=settings.bot.BOT_HOST, port=settings.bot.BOT_PORT, reload=True)
