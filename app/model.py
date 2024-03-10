"""Module for open and close ML model."""
import logging
import os

from playlist_selection.models import get_model_class
from playlist_selection.models.model import BaseModel

LOGGER = logging.getLogger(__name__)

MODEL: BaseModel | None = None

def open_model():
    """Open model and save it to global."""
    global MODEL
    if MODEL is not None:
        return MODEL

    model_class = get_model_class(name=os.environ["PLAYLIST_SELECTION_MODEL_CLASS"])
    MODEL = model_class.open(
        bucket_name=os.environ["PLAYLIST_SELECTION_S3_BUCKET_NAME"],
        model_name=os.environ["PLAYLIST_SELECTION_MODEL_NAME"],
        profile_name=os.environ.get("PLAYLIST_SELECTION_S3_PROFILE_NAME"),
    )
    LOGGER.info("Model %s loaded, version: %s", model_class, os.environ["PLAYLIST_SELECTION_MODEL_NAME"])
    return MODEL

def close_model():
    """Close model, clear cache etc."""
    global MODEL
    MODEL = None
