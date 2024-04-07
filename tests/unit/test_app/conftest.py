from collections.abc import AsyncIterator, Iterable

import fastapi
import pytest
import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy import event
from sqlalchemy.ext import asyncio as sa_asyncio

from unit.utils import db
from unittest.mock import AsyncMock

@pytest.fixture
async def create_empty_database() -> AsyncIterator[None]:
    from app import config

    async for _ in db.create_database(config.get_settings().pg_dsn_revealed):
        yield


@pytest.fixture
async def create_database(create_empty_database: None, async_engine: sa_asyncio.AsyncEngine) -> AsyncIterator[None]:
    from app.db import models


    async with async_engine.begin() as connection:
        await connection.run_sync(models.Base.metadata.create_all)
    await async_engine.dispose()
    yield
    # async with async_engine.connect() as connection:
    #     has_garbage = (await connection.execute(sa.text("select * from tracks"))).scalar()
    # if has_garbage:
    #     raise ValueError
    async with async_engine.begin() as connection:
        await connection.run_sync(models.Base.metadata.drop_all)


@pytest.fixture
async def transactional_session(async_engine: sa_asyncio.AsyncEngine) -> AsyncIterator[sa_asyncio.AsyncSession]:
    connection = await async_engine.connect()
    transaction = await connection.begin()
    async_sessionmaker = sa_asyncio.async_sessionmaker(
        async_engine, expire_on_commit=False, class_=sa_asyncio.AsyncSession
    )
    async_session = async_sessionmaker(bind=connection)
    nested: sa_asyncio.engine.AsyncTransaction | sqlalchemy.engine.base.NestedTransaction = (
        await connection.begin_nested()
    )

    @event.listens_for(async_session.sync_session, "after_transaction_end")
    def end_savepoint(session: sqlalchemy.orm.Session, transaction: sqlalchemy.engine.base.Transaction) -> None:
        nonlocal nested

        if not nested.is_active:
            sync_connection = connection.sync_connection
            if not sync_connection:
                raise ValueError
            nested = sync_connection.begin_nested()

    yield async_session

    await transaction.rollback()
    await async_session.close()
    await connection.close()


@pytest.fixture
def app(create_database: None, transactional_session: sa_asyncio.AsyncSession) -> Iterable[fastapi.FastAPI]:
    from app import dependencies

    async def get_session() -> AsyncIterator[sa_asyncio.AsyncSession]:
        yield transactional_session

    from app.main import app

    # TODO: override spotify dependencies
    app.dependency_overrides[dependencies.SpotifyAuthDependency] = AsyncMock()
    app.dependency_overrides[dependencies.get_session] = get_session

    yield app
