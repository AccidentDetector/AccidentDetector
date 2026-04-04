from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = 'changeme'

    # service URLs — add new services here
    # each teammate adds their service URL when ready
    fall_detection_url    : str = 'http://fall-detection:8001'
    fire_detection_url    : str = ''
    violence_detection_url: str = ''

    class Config:
        env_file = '.env'


settings = Settings()

# registry — only include services that have a URL configured
# gateway auto-discovers available services from this
SERVICE_REGISTRY: dict[str, str] = {
    k: v for k, v in {
        'fall-detection'     : settings.fall_detection_url,
        'fire-detection'     : settings.fire_detection_url,
        'violence-detection' : settings.violence_detection_url,
    }.items() if v  # skip empty URLs
}
