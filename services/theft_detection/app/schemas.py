from pydantic import BaseModel

class PredictResponse(BaseModel):
    model: str = 'theft-detection'
    version: str = '1.0.0'
    alert: bool
    confidence: float
    class_name: str
    inference_ms: float

class HealthResponse(BaseModel):
    status: str
    model: str = 'theft-detection'
    version: str = '1.0.0'
    model_loaded: bool