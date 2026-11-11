"""Runtime configuration for tsalign (env override supported)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    DB_NAME: str = "tsalign_db"
    DB_USER: str = "tsalign_user"
    DB_PASSWORD: str = "tsalign_pwd"
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    JWT_SECRET: str = "tsalign-demo-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    REDIS_URL: str = "redis://redis:6379/0"
    ARTIFACT_DIR: str = "/data/artifacts"

    RATE_WINDOW_SECONDS: int = 60
    RATE_WINDOW_MAX: int = 120
    DAILY_JOB_QUOTA: int = 40

    SEED_DEMO: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
