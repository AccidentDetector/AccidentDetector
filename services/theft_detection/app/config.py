from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_path: str = 'weights/crime_detection_scripted.pt'
    sequence_length: int = 16
    conf_threshold: float = 0.50
    alert_class: str = 'Robbery'
    class_names: list = ['Normal', 'Robbery']
    img_size: int = 224
    stride: int = 1

    class Config:
        env_file = '.env'
        protected_namespaces = ('settings_',)

settings = Settings()