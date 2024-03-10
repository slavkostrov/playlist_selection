"""Baseline implementation of playlist selection web app."""
import logging
import logging.config
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import api, web
from app.model import close_model, open_model

LOGGER = logging.getLogger(__name__)

@asynccontextmanager
async def model_lifespan(app: FastAPI):
    """Open/close model logic."""
    open_model()
    yield
    close_model()

app = FastAPI(debug=True, lifespan=model_lifespan)

app.secret_key = os.urandom(64)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

app.include_router(router=api.router)
app.include_router(router=web.router)

web.setup_handlers(app=app)
