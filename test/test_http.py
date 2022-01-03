import pytest
from httpx import AsyncClient
from dsnetserver.main import app
from dsnetserver import __version__

pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Datashare Network Server version %s" % __version__}