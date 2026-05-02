from pydantic import BaseModel
from typing import List


class Detection(BaseModel):
    class_name: str
    class_id: int
    confidence: float


class PredictResponse(BaseModel):
    model: str = "suspicious-action-detection"
    version: str = "1.0.0"
    detections: List[Detection]
    count: int
    inference_ms: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool