from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/dev.db"
    app_tz: str = "UTC"
    cf_access_team_domain: str | None = None
    cf_access_aud: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
