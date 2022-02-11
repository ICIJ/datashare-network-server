from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import List

import databases
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.types import Scope, Receive, Send
from starlette.websockets import WebSocket

from dsnetserver import __version__
from dsnet.logger import logger, add_stdout_handler
from dsnetserver.models import pigeonhole_message_table, broadcast_query_table
from sqlalchemy import insert
from dsnet.message import PigeonHoleNotification

DATABASE_URL = os.getenv('DS_DATABASE_URL', 'sqlite:///dsnet.db')
database = databases.Database(DATABASE_URL)


class BulletinBoard(WebSocketEndpoint):
    encoding = 'bytes'
    connections: List[WebSocket] = list()

    def __init__(self, scope: Scope, receive: Receive, send: Send):
        super().__init__(scope, receive, send)

    async def on_connect(self, websocket):
        BulletinBoard.connections.append(websocket)
        await websocket.accept()

    async def on_disconnect(self, websocket, close_code):
        BulletinBoard.connections.remove(websocket)

    @classmethod
    async def broadcast(cls, data):
        logger.debug(f"broadcasting to {len(cls.connections)} clients")
        for connection in cls.connections:
            await connection.send_bytes(data)


async def homepage(_):
    return JSONResponse({"message": "Datashare Network Server version %s" % __version__})


async def broadcast(request):
    message = await request.body()
    stmt = insert(broadcast_query_table).values(received_at=datetime.now(), message=message)
    await database.execute(stmt)
    await BulletinBoard.broadcast(message)
    return Response()


class PigeonHole(HTTPEndpoint):

    async def post(self, request):
        address = request.path_params['address']
        message = await request.body()
        stmt = insert(pigeonhole_message_table). \
            values(received_at=datetime.now(), message=message, address=address)
        await database.execute(stmt)
        await BulletinBoard.broadcast(PigeonHoleNotification.from_address(bytes.fromhex(address)).to_bytes())
        return Response()

    async def get(self, request):
        address = request.path_params['address']
        stmt = pigeonhole_message_table.select().where(pigeonhole_message_table.c.address == address)
        ph = await database.fetch_one(stmt)
        return Response(media_type="application/octet-stream", content=ph.message)


routes = [
    Route('/', homepage),
    Route('/bb/broadcast', broadcast, methods=['POST']),
    WebSocketRoute('/notifications', BulletinBoard),
    Mount('/ph', routes=[
        Route('/{address:str}', PigeonHole, methods=['GET', 'POST']),
    ])
]

add_stdout_handler(level=logging.DEBUG)
app = Starlette(debug=True, routes=routes,
                on_startup=[database.connect],
                on_shutdown=[database.disconnect])
