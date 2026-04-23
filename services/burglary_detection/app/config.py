from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_path: str = 'weights/crime_detection_improved.pt'   
    sequence_length: int = 16
    conf_threshold: float = 0.50       
    alert_class: str = 'Burglary'      
    class_names: list = ['Normal', 'Burglary']   
    img_size: int = 224

    class Config:
        env_file = '.env'
        protected_namespaces = ('settings_',)

settings = Settings()