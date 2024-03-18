"""Module with config for application."""
import functools

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Config class for application."""
    model_config = pydantic_settings.SettingsConfigDict(env_file=".env_db", env_file_encoding="utf-8")

    # Postgres
    PGUSER: str = "user"
    PGPASSWORD: pydantic.SecretStr = "pass"  # type: ignore[assignment]
    PGHOST: str = "localhost"
    PGPORT: int = 5432
    PGDATABASE: str = ""
    PGSSLMODE: str = "allow"
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
    PLAYLIST_SELECTION_S3_BUCKET_NAME: str = "bucket"
    PLAYLIST_SELECTION_S3_PROFILE_NAME: str = "default"
    PLAYLIST_SELECTION_S3_ENDPOINT_URL: str = "http://storage.yandexcloud.net"

    # Redis
    REDIS_HOST: str
    REDIS_PORT: str

    # Model
    PLAYLIST_SELECTION_MODEL_NAME: str
    PLAYLIST_SELECTION_MODEL_CLASS: str

    # Spotify credentials
    PLAYLIST_SELECTION_CLIENT_ID: pydantic.SecretStr
    PLAYLIST_SELECTION_CLIENT_SECRET: pydantic.SecretStr

    # Playlist Selection app
    PLAYLIST_SELECTION_CALLBACK_URL: str = "http://127.0.0.1:5000/callback/"

    # Playlist Selection bot
    BOT_TOKEN: pydantic.SecretStr

@functools.lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
