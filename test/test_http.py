import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine

from dsnetserver.main import app
from dsnetserver import __version__
from dsnetserver.main import DATABASE_URL
from dsnetserver.models import metadata

pytest_plugins = ('pytest_asyncio',)
db = None


def setup_module(module):
    global db
    db = create_engine(DATABASE_URL)
    metadata.create_all(db)


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Datashare Network Server version %s" % __version__}


@pytest.mark.asyncio
async def test_post_get_ph_message():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/ph/address", data=b'binary message')
        assert response.status_code == 200

        response = await ac.get("/ph/address")
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/octet-stream'
        assert response.content == b'binary message'
