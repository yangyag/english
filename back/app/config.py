from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    pghost: str = "127.0.0.1"
    pgport: int = 5432
    pguser: str
    pgpassword: str
    pgdatabase: str = "app"
    pgschema: str = "english"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{quote_plus(self.pguser)}:{quote_plus(self.pgpassword)}"
            f"@{self.pghost}:{self.pgport}/{self.pgdatabase}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
