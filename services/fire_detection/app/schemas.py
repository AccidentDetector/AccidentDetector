from pydantic import BaseModel
from typing import List


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
    model        : str = 'fire-detection'
    version      : str = '1.0.0'
    alert        : bool
    detections   : List[Detection]
    count        : int
    inference_ms : float


class HealthResponse(BaseModel):
    status       : str
    model        : str = 'fire-detection'
    version      : str = '1.0.0'
    model_loaded : bool
