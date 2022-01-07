from dsnetserver import __version__
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Datashare Network Server version %s" % __version__}

