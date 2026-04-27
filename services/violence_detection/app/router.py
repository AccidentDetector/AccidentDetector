import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.model import detector
from app.schemas import HealthResponse, PredictResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/health', response_model=HealthResponse)
def health():
    return HealthResponse(status='ok', model_loaded=detector.loaded)


@router.post('/predict', response_model=PredictResponse)
async def predict(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=415, detail='file must be a video')

    temp_path = None
    try:
        suffix   = os.path.splitext(file.filename or '')[1].lower() or '.mp4'
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail='empty file')

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        dets, ms = detector.predict(temp_path)
        return PredictResponse(detections=dets, count=len(dets), inference_ms=ms)

    except HTTPException:
        raise
    except Exception:
        logger.exception('inference failed')
        raise HTTPException(status_code=500, detail='inference failed')
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f'failed to remove temp file: {e}')


@router.post('/predict/annotated')
async def predict_annotated():
    raise HTTPException(status_code=501, detail='annotated video inference not implemented')
