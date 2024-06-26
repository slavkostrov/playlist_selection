"""Baseline implementation of playlist selection web app."""
import logging
import logging.config
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext import asyncio as sa_asyncio

from app import api, web
from app.config import get_settings
from app.model import open_model
from app.worker import app as celery_app
from playlist_selection.models.model import DummyModel
from playlist_selection.parsing.parser import SpotifyParser

LOGGER = logging.getLogger(__name__)

@asynccontextmanager
async def model_lifespan(app: FastAPI):
    """Open/close model logic."""
    settings = get_settings()

    try:
        model = open_model(settings=settings)
    except Exception as e:
        LOGGER.exception("got exception while load model", exc_info=e)
        model = DummyModel()

    async_engine = sa_asyncio.create_async_engine(settings.pg_dsn_revealed, pool_pre_ping=True)
    async_session = sa_asyncio.async_sessionmaker(bind=async_engine, expire_on_commit=False)
    parser = SpotifyParser(
        client_id=settings.CLIENT_ID.get_secret_value(),
        client_secret=settings.CLIENT_SECRET.get_secret_value(),
    )

    context = dict(
        model=model,
        async_session=async_session,
        settings=settings,
        parser=parser,
    )
    yield context

    await async_engine.dispose()

description = """
Playlist Selection API helps you recommend awesome songs. 🎧

## PREDICT 🎱

With this handlers you can:
- **search** songs on Spotify and get their metadta
- **generate** song recommendations based on chosen songs

## AUTH 🔐

Helps you with authorization on Spotify:
- **login** in you Spotify account for futher app usage
- **callback** to the app and get your session token
- **logout** from your Spotify account

## GENERATE 🎨

Useful handlers for creating playlist:
- **generate** playlist from a request
- **create** playlist of generated songs and save to your Spotify
- **requests/{request_id}** your previsous or current app usage
- **my** generated playlists
- **my/requests/{request_id}** defenite generated playlist

"""

settings = get_settings()
app = FastAPI(
    title="Playlist Selection App",
    description=description,
    summary="App for creating song recommendation's playlist",
    version="0.0.1",
    lifespan=model_lifespan,
    debug=settings.DEBUG,
)
app.celery_app = celery_app

app.secret_key = os.urandom(64)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

app.include_router(router=api.router)
app.include_router(router=web.router)

web.setup_handlers(app=app)
