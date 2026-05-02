from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io

from app.schemas import (
    PredictResponse,
    HealthResponse,
)

from app.model import SuspiciousActionDetector

router = APIRouter()

detector = SuspiciousActionDetector()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=True,
    )


@router.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()

        image = Image.open(
            io.BytesIO(contents)
        ).convert("RGB")

        detections, inference_ms = detector.predict(image)

        return PredictResponse(
            detections=detections,
            count=len(detections),
            inference_ms=inference_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )