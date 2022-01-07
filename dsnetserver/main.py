import os

import databases
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from dsnetserver import __version__

DATABASE_URL = os.getenv('DS_DATABASE_URL')
database = databases.Database(DATABASE_URL)


async def homepage(_):
    return JSONResponse({"message": "Datashare Network Server version %s" % __version__})

routes = [
    Route('/', homepage)
]

app = Starlette(debug=True, routes=routes)
