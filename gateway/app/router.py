import httpx
import logging
from fastapi import APIRouter, File, UploadFile, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import settings, SERVICE_REGISTRY
from .stream_processor import stream_manager

logger  = logging.getLogger(__name__)
router  = APIRouter()
TIMEOUT = 30.0


def verify_api_key(x_api_key: str):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail='invalid api key')


def get_service_url(model_name: str) -> str:
    url = SERVICE_REGISTRY.get(model_name)
    if not url:
        raise HTTPException(
            status_code=404,
            detail=f'model {model_name!r} not found. available: {list(SERVICE_REGISTRY.keys())}',
        )
    return url


async def forward_to_service(url: str, file: UploadFile, contents: bytes) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(
                f'{url}/predict',
                files={'file': (file.filename, contents, file.content_type)},
            )
            return r
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail='service timed out')
        except Exception as e:
            logger.error(f'service error: {e}')
            raise HTTPException(status_code=502, detail='service unavailable')


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
    return {
        'gateway'        : 'ok',
        'services'       : statuses,
        'active_streams' : stream_manager.active_cameras(),
    }


@router.get('/models', tags=['System'])
def list_models():
    return {'models': list(SERVICE_REGISTRY.keys())}


# fall detection

@router.get('/fall-detection/health', tags=['Fall Detection'])
async def fall_health():
    url = get_service_url('fall-detection')
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='fall-detection service unreachable')


@router.post('/fall-detection/predict', tags=['Fall Detection'])
async def fall_predict(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')

    url      = get_service_url('fall-detection')
    contents = await file.read()
    r        = await forward_to_service(url, file, contents)
    return JSONResponse(status_code=r.status_code, content=r.json())


@router.post('/fall-detection/predict/annotated', tags=['Fall Detection'])
async def fall_predict_annotated(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')

    url      = get_service_url('fall-detection')
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


# fire detection

@router.get('/fire-detection/health', tags=['Fire Detection'])
async def fire_health():
    url = get_service_url('fire-detection')
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='fire-detection service unreachable')


@router.post('/fire-detection/predict', tags=['Fire Detection'])
async def fire_predict(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')
    url      = get_service_url('fire-detection')
    contents = await file.read()
    r        = await forward_to_service(url, file, contents)
    return JSONResponse(status_code=r.status_code, content=r.json())


@router.post('/fire-detection/predict/annotated', tags=['Fire Detection'])
async def fire_predict_annotated(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')
    url      = get_service_url('fire-detection')
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
            logger.error(f'fire annotated error: {e}')
            raise HTTPException(status_code=502, detail='service unavailable')




@router.get('/violence-detection/health', tags=['Violence Detection'])
async def violence_health():
    url = get_service_url('violence-detection')
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='violence-detection service unreachable')


@router.post('/violence-detection/predict', tags=['Violence Detection'])
async def violence_predict(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)

    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=415, detail='file must be a video')

    url      = get_service_url('violence-detection')
    contents = await file.read()
    r        = await forward_to_service(url, file, contents)
    return JSONResponse(status_code=r.status_code, content=r.json())


@router.get('/theft-detection/health', tags=['Theft Detection'])
async def theft_health():
    url = get_service_url('theft-detection')
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='theft-detection service unreachable')


@router.post('/theft-detection/predict/batch', tags=['Theft Detection'])
async def theft_predict_batch(
    files: list[UploadFile] = File(...),
    x_api_key: str = Header(...),
    camera_id: str = 'default',
):
    verify_api_key(x_api_key)
    
    url = get_service_url('theft-detection')

    form_files = []
    for i, file in enumerate(files):
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=415, detail=f'File {i} must be an image')
        contents = await file.read()
        form_files.append(("files", (file.filename, contents, file.content_type)))
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(
                f'{url}/predict/batch',
                params={'camera_id': camera_id},
                files=form_files,
            )
            return JSONResponse(status_code=r.status_code, content=r.json())
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail='service timed out')
        except Exception as e:
            logger.error(f'theft batch error: {e}')
            raise HTTPException(status_code=502, detail='service unavailable')

@router.get('/burglary-detection/health', tags=['Burglary Detection'])
async def burglary_health():
    url = get_service_url('burglary-detection')
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='burglary-detection service unreachable')
        
@router.post('/burglary-detection/predict/batch', tags=['Burglary Detection'])
async def burglary_predict_batch(
    files: list[UploadFile] = File(...),
    x_api_key: str = Header(...),
    camera_id: str = 'default',
):
    verify_api_key(x_api_key)
    url = get_service_url('burglary-detection')
    form_files = []
    for i, file in enumerate(files):
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=415, detail=f'File {i} must be an image')
        contents = await file.read()
        form_files.append(("files", (file.filename, contents, file.content_type)))
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(
                f'{url}/predict/batch',
                params={'camera_id': camera_id},
                files=form_files,
            )
            return JSONResponse(status_code=r.status_code, content=r.json())
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail='service timed out')
        except Exception as e:
            logger.error(f'burglary batch error: {e}')
            raise HTTPException(status_code=502, detail='service unavailable')
        

# person model

@router.get('/person_model/health', tags=['Person Model'])
async def fall_health():
    url = get_service_url('person_model')
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f'{url}/health')
            return r.json()
        except Exception:
            raise HTTPException(status_code=502, detail='person_model service unreachable')


@router.post('/person_model/predict', tags=['Person Model'])
async def fall_predict(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')

    url      = get_service_url('person_model')
    contents = await file.read()
    r        = await forward_to_service(url, file, contents)
    return JSONResponse(status_code=r.status_code, content=r.json())


@router.post('/person_model/predict/annotated', tags=['Person Model'])
async def fall_predict_annotated(
    file     : UploadFile = File(...),
    x_api_key: str = Header(...),
):
    verify_api_key(x_api_key)
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')

    url      = get_service_url('person_model')
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
        
#Другие ML сервисы членов команды в том же паттерне

# @router.get('/fire-detection/health', tags=['Fire Detection'])
# async def fire_health(): ...
#
# @router.post('/fire-detection/predict', tags=['Fire Detection'])
# async def fire_predict(...): ...
#
# @router.post('/fire-detection/predict/annotated', tags=['Fire Detection'])
# async def fire_predict_annotated(...): ...
