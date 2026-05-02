from fastapi import FastAPI

from app.router import router


app = FastAPI(
    title="Suspicious Action Detection Service",
    version="1.0.0",
)


app.include_router(router)