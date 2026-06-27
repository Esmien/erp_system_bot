import httpx
import pytest
from httpx import ASGITransport

from bot.main import app


@pytest.fixture
async def client():
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
