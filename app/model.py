"""Module for open and close ML model."""
import logging

from app.config import Settings
from playlist_selection.models import get_model_class
from playlist_selection.models.model import BaseModel

LOGGER = logging.getLogger(__name__)

MODEL: BaseModel | None = None

def open_model(settings: Settings):
    """Open model and save it to global."""
    global MODEL
    if MODEL is not None:
        return MODEL

    model_class = get_model_class(name=settings.MODEL_CLASS)
    MODEL = model_class.open(
        bucket_name=settings.S3_BUCKET_NAME,
        model_name=settings.MODEL_NAME,
        profile_name=settings.S3_PROFILE_NAME,
    )
    LOGGER.info("Model %s loaded, version: %s", model_class, settings.MODEL_NAME)
    return MODEL

def close_model():
    """Close model, clear cache etc."""
    global MODEL
    MODEL = None
