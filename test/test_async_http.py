import asyncio
from datetime import datetime

import pytest_asyncio
from sqlalchemy import create_engine
import pytest
from starlette.testclient import TestClient

from dsnetserver.main import setup_app
from dsnetserver.main import DATABASE_URL, database
from dsnetserver.models import metadata

db = None


@pytest_asyncio.fixture
async def app():
    yield setup_app()


@pytest_asyncio.fixture
async def connect_disconnect_db():
    engine = create_engine(DATABASE_URL)
    metadata.create_all(engine)
    await database.connect()
    yield
    metadata.drop_all(engine)
    await database.disconnect()


@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_post_broadcast(connect_disconnect_db, app):
    alice = TestClient(app)
    bob = TestClient(app)
    response = alice.post("/bb/broadcast", data=b'query payload')
    ts = datetime.utcnow()
    with bob.websocket_connect(f'/notifications?ts={ts.timestamp() - 200}') as websocket:
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == b'query payload'


@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_post_pigeon_hole(connect_disconnect_db, app):
    alice = TestClient(app)
    bob = TestClient(app)
    response = alice.post("/ph/deadbeef", data=b'response payload')
    ts = datetime.utcnow()
    with bob.websocket_connect(f'/notifications?ts={ts.timestamp() - 200}') as websocket:
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == b'\xd8f\x81\xa7adr_hex\xa6deadbe'