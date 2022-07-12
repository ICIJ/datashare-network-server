import asyncio
from datetime import datetime

from sqlalchemy import create_engine
import pytest
from starlette.testclient import TestClient

from dsnetserver.main import app
from dsnetserver.main import DATABASE_URL, database
from dsnetserver.models import metadata, broadcast_query_table

db = None


def setup_module(module):
    global db
    db = create_engine(DATABASE_URL)
    metadata.create_all(db)


def teardown_module(module):
    asyncio.run(database.execute(broadcast_query_table.delete()))


@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_post_broadcast():
    alice = TestClient(app)
    bob = TestClient(app)
    response = alice.post("/bb/broadcast", data=b'query payload')
    ts = datetime.utcnow()
    with bob.websocket_connect(f'/notifications?ts={ts.timestamp() - 200}') as websocket:
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == b'query payload'

