"""Application configuration settings."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """App settings (env variables)."""
    secret_key: str = "super-secret-key"
    algo: str = "HS256"
    database_url: str = "sqlite:///game.db"
    access_token_expire_minutes: int = 30

settings = Settings()
