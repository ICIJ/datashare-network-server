import pytest
from sqlalchemy import create_engine
import asyncio
import dsnet

import pytest
from sqlalchemy import create_engine
import msgpack
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
    assert response.json() == {"message": "Datashare Network Server version %s" % __version__,
                               "server_version": __version__,
                               "core_version": dsnet.__version__}


def test_post_get_ph_message():
    client = TestClient(app)

    response = client.post("/ph/deadbeef", content=b'binary message')
    assert response.status_code == 200

    response = client.get("/ph/deadbeef")
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/octet-stream'
    assert response.content == b'binary message'


def test_post_get_ph_message_with_wrong_address():
    client = TestClient(app)

    response = client.get("/ph/unknown")
    assert response.status_code == 404


def test_get_ph_messages_by_shortened_address():
    client = TestClient(app)

    response = client.post("/ph/beefc0fe", content=b'binary message 1')
    assert response.status_code == 200

    response = client.post("/ph/beefc0c0", content=b'binary message 2')
    assert response.status_code == 200

    response = client.get("/ph/beefc0")
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/octet-stream'
    messages = msgpack.unpackb(response.content, raw=False)
    assert len(messages) == 2
    assert messages[0] == b'binary message 1'
    assert messages[1] == b'binary message 2'


@pytest.mark.timeout(5)
def test_post_broadcast():
    client = TestClient(app)

    with client.websocket_connect('/notifications') as websocket:
        response = client.post("/bb/broadcast", content=b'query payload')
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == b'query payload'


@pytest.mark.timeout(5)
def test_post_response():
    client = TestClient(app)

    with client.websocket_connect('/notifications') as websocket:
        response = client.post("/ph/deadbeef", content=b'response data')
        assert response.status_code == 200
        data = websocket.receive_bytes()
        assert data == PigeonHoleNotification('deadbe').to_bytes()


