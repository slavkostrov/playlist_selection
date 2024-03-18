"""Module for open and close ML model."""
import logging

from app.config import get_settings
from playlist_selection.models import get_model_class
from playlist_selection.models.model import BaseModel

LOGGER = logging.getLogger(__name__)

MODEL: BaseModel | None = None
settings = get_settings()

def open_model():
    """Open model and save it to global."""
    global MODEL
    if MODEL is not None:
        return MODEL

    model_class = get_model_class(name=settings.PLAYLIST_SELECTION_MODEL_CLASS)
    MODEL = model_class.open(
        bucket_name=settings.PLAYLIST_SELECTION_S3_BUCKET_NAME,
        model_name=settings.PLAYLIST_SELECTION_MODEL_NAME,
        profile_name=settings.PLAYLIST_SELECTION_S3_PROFILE_NAME,
    )
    LOGGER.info("Model %s loaded, version: %s", model_class, settings.PLAYLIST_SELECTION_MODEL_NAME)
    return MODEL

def close_model():
    """Close model, clear cache etc."""
    global MODEL
    MODEL = None
