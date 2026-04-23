import logging
from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from app.router import router

handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

app = FastAPI(
    title='Theft Model Service',
    version='1.0.0',
    docs_url='/docs',
    redoc_url=None,
)

app.include_router(router)
