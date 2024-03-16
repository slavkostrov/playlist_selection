import functools

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
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
        return f"postgresql+asyncpg://{self.PGUSER}:{self.PGPASSWORD.get_secret_value()}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}?ssl={self.PGSSLMODE}"

    @property
    def pg_dsn_revealed_sync(self) -> str:
        return f"postgresql+psycopg2://{self.PGUSER}:{self.PGPASSWORD.get_secret_value()}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"

    @property
    def pg_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
