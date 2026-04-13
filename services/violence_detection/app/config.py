from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = 'weights/violence.pt'
    class_names: list = ['Normal', 'Violence']
    conf_threshold: float = 0.40
    alert_threshold: float = 0.65
    alert_class: str = 'Violence'

    clip_duration_sec: float = 1.0
    clip_num_frames: int = 16
    image_size: int = 112

    class Config:
        env_file = '.env'


settings = Settings()