from collections.abc import AsyncGenerator, Iterable

import asgi_lifespan
import fastapi
import httpx
import pytest
from sqlalchemy.ext import asyncio as sa_asyncio


@pytest.fixture(scope="session")
def postgres_dsn() -> Iterable[str]:
    from app import config

    return config.Settings().pg_dsn_revealed


@pytest.fixture
async def async_engine(postgres_dsn: str) -> AsyncGenerator[sa_asyncio.AsyncEngine, None]:
    engine = sa_asyncio.create_async_engine(postgres_dsn)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(app: fastapi.FastAPI, shutdown_timeout: int = 10) -> AsyncGenerator[httpx.AsyncClient, None]:
    from app import config

    settings = config.get_settings()
    async with asgi_lifespan.LifespanManager(app, shutdown_timeout=shutdown_timeout):
        async with httpx.AsyncClient(app=app, base_url=f"http://localhost{settings.PREFIX}") as client:
            yield client
