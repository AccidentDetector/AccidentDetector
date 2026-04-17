import io
import logging

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import settings
from app.model import detector
from app.schemas import HealthResponse, PredictResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def decode_image(data: bytes) -> np.ndarray:
    nparr = np.frombuffer(data, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail='cannot decode image')
    return img


@router.get('/health', response_model=HealthResponse)
def health():
    return HealthResponse(status='ok', model_loaded=detector.loaded)


@router.post('/predict', response_model=PredictResponse)
async def predict(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')

    try:
        contents        = await file.read()
        img             = decode_image(contents)
        alert, dets, ms = detector.predict(img)
        logger.info(f'predict | alert={alert} detections={len(dets)} file={file.filename}')
        return PredictResponse(alert=alert, detections=dets, count=len(dets), inference_ms=ms)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'inference failed: {e}')
        raise HTTPException(status_code=500, detail='inference failed')


@router.post('/predict/annotated')
async def predict_annotated(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='file must be an image')

    try:
        contents  = await file.read()
        img       = decode_image(contents)
        result    = detector.model.predict(img, conf=settings.conf_threshold, verbose=False)[0]
        annotated = result.plot()

        alert = any(
            settings.class_names[int(b.cls.item())] == settings.alert_class
            and b.conf.item() >= settings.alert_threshold
            for b in (result.boxes or [])
        )

        _, buffer = cv2.imencode('.jpg', annotated)
        return StreamingResponse(
            io.BytesIO(buffer.tobytes()),
            media_type='image/jpeg',
            headers={'X-Alert': str(alert).lower()},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'annotated inference failed: {e}')
        raise HTTPException(status_code=500, detail='inference failed')
