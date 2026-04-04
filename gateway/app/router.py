import httpx
import logging
from fastapi import APIRouter, File, UploadFile, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import settings, SERVICE_REGISTRY

logger  = logging.getLogger(__name__)
router  = APIRouter()
TIMEOUT = 30.0


def verify_api_key(x_api_key: str):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail='invalid api key')


def decode_and_forward(url: str):

    async def _predict(file: UploadFile = File(...), x_api_key: str = Header(...)):
        verify_api_key(x_api_key)
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=415, detail='file must be an image')
        contents = await file.read()
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                r = await client.post(
                    f'{url}/predict',
                    files={'file': (file.filename, contents, file.content_type)},
                )
                return JSONResponse(status_code=r.status_code, content=r.json())
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail='service timed out')
            except Exception as e:
                logger.error(f'predict error: {e}')
                raise HTTPException(status_code=502, detail='service unavailable')

    async def _predict_annotated(file: UploadFile = File(...), x_api_key: str = Header(...)):
        verify_api_key(x_api_key)
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=415, detail='file must be an image')
        contents = await file.read()
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                r = await client.post(
                    f'{url}/predict/annotated',
                    files={'file': (file.filename, contents, file.content_type)},
                )
                return StreamingResponse(
                    content=r.aiter_bytes(),
                    media_type='image/jpeg',
                    headers={'X-Alert': r.headers.get('X-Alert', 'false')},
                )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail='service timed out')
            except Exception as e:
                logger.error(f'annotated error: {e}')
                raise HTTPException(status_code=502, detail='service unavailable')

    return _predict, _predict_annotated


#system

@router.get('/health', tags=['System'])
async def gateway_health():
    statuses = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in SERVICE_REGISTRY.items():
            try:
                r = await client.get(f'{url}/health')
                statuses[name] = r.json()
            except Exception:
                statuses[name] = {'status': 'unreachable'}
    return {'gateway': 'ok', 'services': statuses}


@router.get('/models', tags=['System'])
def list_models():
    return {'models': list(SERVICE_REGISTRY.keys())}


#fall detection

_fall_predict, _fall_annotated = decode_and_forward(settings.fall_detection_url)

@router.get('/fall-detection/health', tags=['Fall Detection'])
async def fall_health():
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{settings.fall_detection_url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='fall-detection service unreachable')

@router.post('/fall-detection/predict', tags=['Fall Detection'])
async def fall_predict(file: UploadFile = File(...), x_api_key: str = Header(...)):
    return await _fall_predict(file=file, x_api_key=x_api_key)

@router.post('/fall-detection/predict/annotated', tags=['Fall Detection'])
async def fall_predict_annotated(file: UploadFile = File(...), x_api_key: str = Header(...)):
    return await _fall_annotated(file=file, x_api_key=x_api_key)
