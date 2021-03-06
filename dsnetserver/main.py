from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import List

import databases
import dsnet
import msgpack
from starlette.applications import Starlette
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

DATABASE_URL = os.getenv('DS_DATABASE_URL', 'sqlite:///dsnet.db')
PREFIX_LEN = 6
database = databases.Database(DATABASE_URL)


class BulletinBoard(WebSocketEndpoint):
    encoding = 'bytes'
    connections: List[WebSocket] = list()

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)

    async def on_connect(self, websocket: WebSocket) -> None:
        BulletinBoard.connections.append(websocket)
        ts_parameter = websocket.query_params.get('ts')
        await websocket.accept()
        if ts_parameter is not None:
            await BulletinBoard.get_broadcast_messages(websocket, datetime.utcfromtimestamp(float(ts_parameter)))

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        BulletinBoard.connections.remove(websocket)

    @staticmethod
    async def get_broadcast_messages(connection: WebSocket, ts: datetime) -> None:
        stmt = select(broadcast_query_table).where(broadcast_query_table.c.received_at >= ts)
        messages = await database.fetch_all(stmt)
        for message in messages:
            await connection.send_bytes(message.message)

    @classmethod
    async def broadcast(cls, data: bytes) -> None:
        logger.debug(f"broadcasting to {len(cls.connections)} clients")
        for connection in cls.connections:
            await connection.send_bytes(data)


async def homepage(_):
    return JSONResponse({"message": f"Datashare Network Server version {__version__}",
                         "server_version": __version__,
                         "core_version": dsnet.__version__})


async def broadcast_query(request):
    message = await request.body()
    return await broadcast_message(message)


async def broadcast_message(message):
    stmt = insert(broadcast_query_table).values(received_at=datetime.utcnow(), message=message)
    await database.execute(stmt)
    await BulletinBoard.broadcast(message)
    return Response()


class PigeonHole(HTTPEndpoint):

    async def post(self, request):
        address = request.path_params['address']
        message = await request.body()
        stmt = insert(pigeonhole_message_table). \
            values(received_at=datetime.now(), message=message, address=address, address_prefix=address[:PREFIX_LEN])
        await database.execute(stmt)
        await broadcast_message(PigeonHoleNotification.from_address(bytes.fromhex(address)).to_bytes())
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


routes = [
    Route('/', homepage),
    Route('/bb/broadcast', broadcast_query, methods=['POST']),
    WebSocketRoute('/notifications', BulletinBoard),
    Mount('/ph', routes=[
        Route('/{address:str}', PigeonHole, methods=['GET', 'POST']),
    ])
]

add_stdout_handler(level=logging.DEBUG)
app = Starlette(debug=True, routes=routes,
                on_startup=[database.connect],
                on_shutdown=[database.disconnect])
