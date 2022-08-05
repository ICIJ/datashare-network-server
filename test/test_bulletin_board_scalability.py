import asyncio
from collections import defaultdict
from typing import Dict, Set

from aiohttp import ClientSession
import pytest
import pytest_asyncio
from sqlalchemy import create_engine

from dsnetserver.main import setup_app, DATABASE_URL
from dsnetserver.models import metadata
from test.server import UvicornTestServer


@pytest_asyncio.fixture
async def setup_db():
    engine = create_engine(DATABASE_URL)
    metadata.create_all(engine)
    yield
    metadata.drop_all(engine)


@pytest_asyncio.fixture
async def startup_and_shutdown_cluster(setup_db):
    cluster = (
        UvicornTestServer(setup_app('redis://redis:6379'), port=12345),
        UvicornTestServer(setup_app('redis://redis:6379'), port=12346)
    )

    for server in cluster:
        await server.up()

    yield

    for server in cluster:
        await server.down()


@pytest_asyncio.fixture
async def sessions(startup_and_shutdown_cluster):
    async with ClientSession() as alice:
        async with ClientSession() as bob:
            yield alice, bob


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_server_bulletin_board_broadcast_scale(startup_and_shutdown_cluster, sessions):
    alice, bob = sessions

    received = defaultdict(set)

    alice_url = "ws://localhost:12346/notifications"
    bob_url = "ws://localhost:12345/notifications"

    t_alice = asyncio.create_task(wait_websocket_notification(alice, alice_url, received, expected_message_nb=2))
    t_bob = asyncio.create_task(wait_websocket_notification(bob, bob_url, received, expected_message_nb=2))

    await alice.post("http://localhost:12346/bb/broadcast", data=b"foo")
    await bob.post("http://localhost:12345/bb/broadcast", data=b"bar")
    await asyncio.wait([t_bob, t_alice])

    assert received[alice_url] == {b"foo", b"bar"}
    assert received[bob_url] == {b"foo", b"bar"}


async def wait_websocket_notification(client: ClientSession, url: str, received: Dict[str, Set[bytes]], expected_message_nb: int):
    async with client.ws_connect(url, timeout=3) as ws:
        for _ in range(expected_message_nb):
            msg = await ws.receive_bytes()
            received[url].add(msg)
