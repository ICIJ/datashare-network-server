import os

import databases
import sqlalchemy

from dsnetserver import __version__
from fastapi import FastAPI


app = FastAPI()
db_url = os.getenv('DS_DATABASE_URL', 'sqlite:///:memory:?cache=shared')
database = databases.Database(db_url)

engine = sqlalchemy.create_engine(
    db_url, connect_args={"check_same_thread": False}
)


@app.get("/")
async def root():
    return {"message": "Datashare Network Server version %s" % __version__}

