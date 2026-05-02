from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = "weights/resnet50_suspicious.pth"

    # binary classes
    class_names: list[str] = [
        "Normal",
        "Suspicious",
    ]

    conf_threshold: float = 0.50

    # compatibility only
    alert_threshold: float = 0.70
    alert_class: str = "Suspicious"

    image_size: int = 224

    class Config:
        env_file = ".env"


settings = Settings()