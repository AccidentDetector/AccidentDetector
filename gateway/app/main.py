import asyncio
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .router import router
from .camera_manager import camera_refresh_loop

handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def lifespan(app: FastAPI):
    logger.info('starting camera refresh loop')
    asyncio.create_task(camera_refresh_loop())
    yield
    logger.info('shutting down')


app = FastAPI(
    title='AccidentDetector API',
    description='Multi-model real-time incident detection for street and building cameras',
    version='1.0.0',
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def log_requests(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    ms       = round((time.time() - start) * 1000, 2)
    logger.info('request', extra={
        'method'  : request.method,
        'path'    : request.url.path,
        'status'  : response.status_code,
        'duration': ms,
    })
    return response


@app.middleware('http')
async def limit_upload_size(request: Request, call_next):
    if request.method == 'POST':
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > 10 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={'error': 'file too large, max 10MB'},
            )
    return await call_next(request)


app.include_router(router, prefix='/api/v1')
