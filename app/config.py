from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    encryption_key_fernet: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    mt5_timeout: int = 30000
    mt5_path: Optional[str] = None
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
