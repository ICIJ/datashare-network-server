import os
from datetime import datetime

import databases
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount
from dsnetserver import __version__
from dsnetserver.models import pigeonhole_message_table, broadcast_query_table
from sqlalchemy import insert

DATABASE_URL = os.getenv('DS_DATABASE_URL', 'sqlite:///dsnet.db')
database = databases.Database(DATABASE_URL)


async def homepage(_):
    return JSONResponse({"message": "Datashare Network Server version %s" % __version__})


async def broadcast(request):
    message = await request.body()
    stmt = insert(broadcast_query_table). \
        values(received_at=datetime.now(), message=message)
    await database.execute(stmt)
    return Response()


class PigeonHole(HTTPEndpoint):

    async def post(self, request):
        address = request.path_params['address']
        message = await request.body()
        stmt = insert(pigeonhole_message_table). \
            values(received_at=datetime.now(), message=message, address=address)
        await database.execute(stmt)
        return Response()

    async def get(self, request):
        address = request.path_params['address']
        stmt = pigeonhole_message_table.select().where(pigeonhole_message_table.c.address == address)
        ph = await database.fetch_one(stmt)
        return Response(media_type="application/octet-stream", content=ph.message)


routes = [
    Route('/', homepage),
    Route('/bb/broadcast', broadcast, methods=['POST']),
    Mount('/ph', routes=[
        Route('/{address:str}', PigeonHole, methods=['GET', 'POST']),
    ])
]

app = Starlette(debug=True, routes=routes,
                on_startup=[database.connect],
                on_shutdown=[database.disconnect])
