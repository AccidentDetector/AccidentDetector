from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = 'changeme'

    fall_detection_url: str = 'http://fall-detection:8001'
    fire_detection_url: str = 'http://fire-detection:8002'
    violence_detection_url: str = 'http://violence-detection:8003'

    backend_url: str = ''
    backend_api_key: str = ''

    frame_interval_sec: float = 1.0
    alert_cooldown_sec: int = 30
    camera_refresh_sec: int = 60

    class Config:
        env_file = Path(__file__).parent.parent.parent / '.env'


settings = Settings()

MODEL_REGISTRY: dict[str, dict] = {
    'fall-detection': {
        'url': settings.fall_detection_url,
        'input_mode': 'image',
        'filename': 'frame.jpg',
        'content_type': 'image/jpeg',
    },
    'fire-detection': {
        'url': settings.fire_detection_url,
        'input_mode': 'image',
        'filename': 'frame.jpg',
        'content_type': 'image/jpeg',
    },
    'violence-detection': {
        'url': settings.violence_detection_url,
        'input_mode': 'video',
        'filename': 'clip.avi',
        'content_type': 'video/x-msvideo',
        'clip_frames': 16,
        'clip_duration_sec': 1.0,
        'clip_fps': 16,
    },
}

MODEL_REGISTRY = {
    name: spec
    for name, spec in MODEL_REGISTRY.items()
    if spec.get('url')
}

IMAGE_MODELS = {
    name: spec
    for name, spec in MODEL_REGISTRY.items()
    if spec.get('input_mode') == 'image'
}

VIDEO_MODELS = {
    name: spec
    for name, spec in MODEL_REGISTRY.items()
    if spec.get('input_mode') == 'video'
}

SERVICE_REGISTRY: dict[str, str] = {
    name: spec['url']
    for name, spec in MODEL_REGISTRY.items()
    if spec.get('url')
}