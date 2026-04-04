from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path      : str   = 'weights/best.pt'
    class_names     : list  = ['Fall', 'Fine', 'Stand']
    conf_threshold  : float = 0.40
    alert_threshold : float = 0.65

    class Config:
        env_file = '.env'


settings = Settings()
