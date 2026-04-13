from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = 'changeme'

    # ML service URLs — add new models here
    fall_detection_url    : str = 'http://fall-detection:8001'
    fire_detection_url    : str = ''
    violence_detection_url: str = ''

    # Go backend integration
    backend_url      : str = ''   # http://qamqor-vision-backend:8080
    backend_api_key  : str = ''   # API key to call their backend

    frame_interval_sec  : float = 1.0    # how often to sample frames per camera
    alert_cooldown_sec  : int   = 30     # min seconds between alerts for same camera
    camera_refresh_sec  : int   = 60     # how often to refresh camera list from backend

    class Config:
        env_file = '.env'


settings = Settings()

SERVICE_REGISTRY: dict[str, str] = {
    k: v for k, v in {
        'fall-detection'     : settings.fall_detection_url,
        'fire-detection'     : settings.fire_detection_url,
        'violence-detection' : settings.violence_detection_url,
    }.items() if v
}
