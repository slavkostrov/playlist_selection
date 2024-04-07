from collections.abc import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext import asyncio as sa_asyncio

# TODO TESTS: fix
POSTGRES_DEFAULT_DB = "postgres"


def _parse_dsn(postgres_dsn: str) -> tuple[URL, str]:
    url = make_url(postgres_dsn)
    database_name = url.database
    if database_name is None:
        raise ValueError("Undefined database name")
    master_url = url.set(database=POSTGRES_DEFAULT_DB)
    return master_url, database_name


async def is_pg_database_created(engine: sa_asyncio.AsyncEngine, database_name: str) -> bool:
    async with engine.connect() as conn:
        return (await conn.execute(sa.text(f"SELECT 1 FROM pg_database WHERE datname='{database_name}'"))).scalar() == 1


async def create_pg_database(engine: sa_asyncio.AsyncEngine, database_name: str) -> None:
    async with engine.execution_options(isolation_level="autocommit").connect() as conn:
        await conn.execute(sa.text(f'CREATE DATABASE "{database_name}"'))


async def ensure_no_database(engine: sa_asyncio.AsyncEngine, database_name: str) -> None:
    database_exists = await is_pg_database_created(engine, database_name)
    if database_exists:
        await drop_database(engine, database_name)


async def create_database(postgres_dsn: str) -> AsyncGenerator[None, None]:
    master_url, database_name = _parse_dsn(postgres_dsn)
    engine = sa_asyncio.create_async_engine(master_url)

    await ensure_no_database(engine, database_name)
    await create_pg_database(engine, database_name)

    await engine.dispose()
    yield
    await drop_database(engine, database_name)
    await engine.dispose()


async def drop_database(engine: sa_asyncio.AsyncEngine, database_name: str) -> None:
    async with engine.execution_options(isolation_level="autocommit").connect() as conn:
        disconnect_users = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{database_name}'
          AND pid <> pg_backend_pid();
        """
        await conn.execute(sa.text(disconnect_users))
        await conn.execute(sa.text(f'DROP DATABASE "{database_name}"'))
    await engine.dispose()
