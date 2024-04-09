from collections.abc import AsyncGenerator

import pytest

from unit.utils import db as db_utils


@pytest.fixture
async def create_database(postgres_dsn: str) -> AsyncGenerator[None, None]:
    async for _ in db_utils.create_database(postgres_dsn):
        yield
