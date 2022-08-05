from __future__ import annotations

import asyncio
import functools
import logging
import os
from datetime import datetime
from typing import List, Optional

import databases
import dsnet
import msgpack
from redis.asyncio import Redis
from starlette.applications import Starlette
from starlette.config import Config
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.types import Scope, Receive, Send
from starlette.websockets import WebSocket

from dsnetserver import __version__
from dsnet.logger import logger, add_stdout_handler
from dsnetserver.models import pigeonhole_message_table, broadcast_query_table
from sqlalchemy import insert, select
from dsnet.message import PigeonHoleNotification


config = Config(".env")
DATABASE_URL = config.get('DS_DATABASE_URL', default='sqlite:///dsnet.db')
REDIS_URL = config.get('DS_REDIS_URL', default=None)

DATASHARE_NETWORK_SERVER_CHANNEL = 'ds_server_channel'
PREFIX_LEN = 6
database = databases.Database(DATABASE_URL)


class BulletinBoard:
    def __init__(self):
        self.connections: List[WebSocket] = []

    def add(self, websocket: WebSocket):
        self.connections.append(websocket)

    def remove(self, websocket):
        self.connections.remove(websocket)

    async def broadcast(self, data: bytes) -> None:
        logger.debug(f"broadcasting to {len(self.connections)} clients")

        stmt = insert(broadcast_query_table).values(received_at=datetime.utcnow(), message=data)
        await database.execute(stmt)
        await self._broadcast(data)

    async def _broadcast(self, data: bytes) -> None:
        for connection in self.connections:
            await connection.send_bytes(data)

    async def broadcast_query(self, request):
        message = await request.body()
        await self.broadcast(message)
        return Response()

    async def resume(self, websocket: WebSocket, ts_parameter: str):
        await BulletinBoard.get_broadcast_messages(websocket, datetime.utcfromtimestamp(float(ts_parameter)))

    @staticmethod
    async def get_broadcast_messages(connection: WebSocket, ts: datetime) -> None:
        stmt = select(broadcast_query_table).where(broadcast_query_table.c.received_at >= ts)
        messages = await database.fetch_all(stmt)
        for message in messages:
            await connection.send_bytes(message.message)

    def start_sync(self):
        pass

    async def stop(self):
        for conn in self.connections:
            await conn.close()


class RedisSyncBulletinBoard(BulletinBoard):
    def __init__(self,  redis: Redis):
        super().__init__()
        self.redis = redis
        self.pubsub = redis.pubsub()
        self._sync_coroutine = None
        self._stop_asked = False

    def start_sync(self):
        self._sync_coroutine = asyncio.create_task(self._broadcast_sync_coroutine())

    async def _broadcast_sync_coroutine(self):
        await self.pubsub.subscribe(DATASHARE_NETWORK_SERVER_CHANNEL)
        while not self._stop_asked:
            data = await self.pubsub.get_message(timeout=2.0)
            if data is not None and data['type'] == 'message':
                await self._broadcast(data['data'])

    async def broadcast(self, data: bytes) -> None:
        logger.debug(f"broadcasting to {len(self.connections)} clients")

        stmt = insert(broadcast_query_table).values(received_at=datetime.utcnow(), message=data)
        await database.execute(stmt)
        await self.redis.publish(DATASHARE_NETWORK_SERVER_CHANNEL, data)

    async def stop(self):
        await super().stop()
        if self._broadcast_sync_coroutine is not None:
            self._stop_asked = True
            await asyncio.wait_for(self._sync_coroutine, timeout=4)
        await self.pubsub.close()


class BulletinBoardEndpoint(WebSocketEndpoint):
    encoding = 'bytes'

    def __init__(self, bulletin_board: BulletinBoard, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)
        self.bulletin_board = bulletin_board

    async def on_connect(self, websocket: WebSocket) -> None:
        self.bulletin_board.add(websocket)
        ts_parameter = websocket.query_params.get('ts')
        await websocket.accept()
        if ts_parameter is not None:
            await self.bulletin_board.resume(websocket, ts_parameter)

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        self.bulletin_board.remove(websocket)


async def homepage(_):
    return JSONResponse({"message": f"Datashare Network Server version {__version__}",
                         "server_version": __version__,
                         "core_version": dsnet.__version__})


class PigeonHole(HTTPEndpoint):
    def __init__(self, bulletin_board: BulletinBoard, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)
        self.bulletin_board = bulletin_board

    async def post(self, request):
        address = request.path_params['address']
        message = await request.body()
        stmt = insert(pigeonhole_message_table). \
            values(received_at=datetime.now(), message=message, address=address, address_prefix=address[:PREFIX_LEN])
        await database.execute(stmt)
        await self.bulletin_board.broadcast(PigeonHoleNotification.from_address(bytes.fromhex(address)).to_bytes())
        return Response()

    async def get(self, request):
        address = request.path_params['address']
        if len(address) == PREFIX_LEN:
            stmt = pigeonhole_message_table.select().where(pigeonhole_message_table.c.address_prefix == address)
            messages = [ph.message for ph in await database.fetch_all(stmt)]
            return Response(media_type="application/octet-stream", content=msgpack.packb(messages, use_bin_type=True))

        else:
            stmt = pigeonhole_message_table.select().where(pigeonhole_message_table.c.address == address)
            ph = await database.fetch_one(stmt)
            return Response(media_type="application/octet-stream", content=ph.message) if ph is not None else Response(status_code=404)


def setup_app(redis_url: Optional[str] = None):
    bulletin_board = RedisSyncBulletinBoard(Redis.from_url(redis_url)) if redis_url is not None else BulletinBoard()
    routes = [
        Route('/', homepage),
        Route('/bb/broadcast', bulletin_board.broadcast_query, methods=['POST']),
        WebSocketRoute('/notifications', functools.partial(BulletinBoardEndpoint, bulletin_board)),
        Mount('/ph', routes=[
            Route('/{address:str}', functools.partial(PigeonHole, bulletin_board), methods=['GET', 'POST']),
        ])
    ]

    add_stdout_handler(level=logging.DEBUG)
    return Starlette(debug=True, routes=routes,
                    on_startup=[database.connect, bulletin_board.start_sync],
                    on_shutdown=[database.disconnect, bulletin_board.stop])


app = setup_app(REDIS_URL)