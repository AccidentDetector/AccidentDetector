from typing import Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, Query
from app.model import detector
from app.schemas import HealthResponse, PredictResponse

logger = logging.getLogger(__name__)
router = APIRouter()

def decode_image(data: bytes) -> np.ndarray:
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail='cannot decode image')
    return img

@router.get('/health', response_model=HealthResponse)
def health():
    return HealthResponse(
        status='ok',
        model_loaded=detector.loaded
    )

@router.post('/predict/batch', response_model=PredictResponse)
async def predict_batch(
    files: list[UploadFile] = File(...),
    camera_id: Optional[str] = Query('default')
):
    """
    Принимает ровно 16 кадров и возвращает один ответ.
    """
    if len(files) != 16:
        raise HTTPException(status_code=400, detail=f'Exactly 16 frames required, got {len(files)}')
    
    frames = []
    for file in files:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=415, detail='All files must be images')
        contents = await file.read()
        img = decode_image(contents)
        frames.append(img)
    
    try:
        alert, confidence, class_name, ms = detector.predict_sequence(frames)
        return PredictResponse(
            alert=alert,
            confidence=round(confidence, 4),
            class_name=class_name,
            inference_ms=ms
        )
    except Exception as e:
        logger.error(f'Batch inference failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))