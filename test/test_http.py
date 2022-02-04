import pytest
from sqlalchemy import create_engine
import asyncio
from starlette.testclient import TestClient
from dsnetserver.main import app
from dsnetserver import __version__
from dsnetserver.main import DATABASE_URL, database
from dsnetserver.models import metadata, pigeonhole_message_table, broadcast_query_table
from dsnet.message import PigeonHoleNotification

db = None


def setup_module(module):
    global db
    db = create_engine(DATABASE_URL)
    metadata.create_all(db)


def teardown_module(module):
    asyncio.run(database.execute(pigeonhole_message_table.delete()))
    asyncio.run(database.execute(broadcast_query_table.delete()))


def test_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Datashare Network Server version %s" % __version__}


def test_post_get_ph_message():
    client = TestClient(app)

    response = client.post("/ph/deadbeef", data=b'binary message')
    assert response.status_code == 200

    response = client.get("/ph/deadbeef")
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/octet-stream'
    assert response.content == b'binary message'


@pytest.mark.timeout(5)
def test_post_broadcast():
    client = TestClient(app)

    with client.websocket_connect('/notifications') as websocket:
        response = client.post("/bb/broadcast", data=b'query payload')
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == b'query payload'


@pytest.mark.timeout(5)
def test_post_response():
    client = TestClient(app)

    with client.websocket_connect('/notifications') as websocket:
        response = client.post("/ph/deadbeef", data=b'response data')
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == PigeonHoleNotification('deadbe').to_bytes()


