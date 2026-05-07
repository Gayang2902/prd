from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    app_name: str = "SecureScope"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://securescope:localdev@localhost:5432/securescope"
    redis_url: str = "redis://localhost:6379/0"
    temporal_host: str = "localhost:7233"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60


settings = Settings()
