import logging

from fastapi import FastAPI
from pythonjsonlogger import json

from .router import router

handler = logging.StreamHandler()
handler.setFormatter(json.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

app = FastAPI(
    title='Fall Detection Service',
    version='1.0',
    docs_url=None,
    redoc_url=None,
)

app.include_router(router)
