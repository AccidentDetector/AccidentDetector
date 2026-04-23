from pydantic import BaseModel
from typing import List

class Detection(BaseModel):
    class_name: str
    confidence: float

class PredictResponse(BaseModel):
    model: str = 'theft-detection'
    version: str = '1.0.0'
    alert: bool
    detections: List[Detection]
    count: int
    inference_ms: float

class HealthResponse(BaseModel):
    status: str
    model: str = 'theft-detection'
    version: str = '1.0.0'
    model_loaded: bool