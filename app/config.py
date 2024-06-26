"""Module with config for application."""
import functools
from typing import Literal

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Config class for application."""
    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="PLAYLIST_SELECTION_", env_file_encoding="utf-8" # env_file=".env",
    )

    # Postgres
    PGUSER: str
    PGPASSWORD: pydantic.SecretStr
    PGHOST: str
    PGPORT: int = 5432
    PGDATABASE: str
    PGSSLMODE: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
    PGSSLROOTCERT: str = "/etc/ssl/certs/ca-certificates.crt"

    @property
    def pg_dsn_revealed(self) -> str:
        """DSN for async connection to psql."""
        return f"postgresql+asyncpg://{self.PGUSER}:{self.PGPASSWORD.get_secret_value()}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}?ssl={self.PGSSLMODE}"

    @property
    def pg_dsn_revealed_sync(self) -> str:
        """DSN for sync connection to psql."""
        return f"postgresql+psycopg2://{self.PGUSER}:{self.PGPASSWORD.get_secret_value()}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"

    @property
    def pg_dsn(self) -> str:
        """DSN for async connection to psql (not revealed)."""
        return f"postgresql+asyncpg://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"

    # S3
    S3_BUCKET_NAME: str
    S3_PROFILE_NAME: str
    S3_ENDPOINT_URL: pydantic.HttpUrl

    # Redis
    REDIS_HOST: str
    REDIS_PORT: str = 6379

    # Model
    MODEL_NAME: str
    MODEL_CLASS: str

    # Spotify credentials
    CLIENT_ID: pydantic.SecretStr
    CLIENT_SECRET: pydantic.SecretStr

    # Playlist Selection app
    CALLBACK_URL: pydantic.HttpUrl
    USER_TOKEN_COOKIE_KEY: str = "playlist_selection_user_id"
    SCOPE: str = "user-library-read playlist-modify-private playlist-read-private"

    DEBUG: bool = True

@functools.lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
