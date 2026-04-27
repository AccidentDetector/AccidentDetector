from pydantic import BaseModel
from typing import List, Optional


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    class_name : str
    class_id   : int
    confidence : float
    box        : BoundingBox


class PredictResponse(BaseModel):
    model        : str = 'fall-detection'
    version      : str = '1.0.0'
    detections   : List[Detection]
    count        : int
    inference_ms : float


class HealthResponse(BaseModel):
    status       : str
    model        : str = 'fall-detection'
    version      : str = '1.0.0'
    model_loaded : bool
