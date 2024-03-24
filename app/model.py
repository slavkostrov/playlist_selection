"""Module for open and close ML model."""
import logging

from app.config import Settings
from playlist_selection.models import get_model_class

LOGGER = logging.getLogger(__name__)

def open_model(settings: Settings):
    """Open model and save it to global."""
    model_class = get_model_class(name=settings.MODEL_CLASS)
    model = model_class.open(
        bucket_name=settings.S3_BUCKET_NAME,
        model_name=settings.MODEL_NAME,
        profile_name=settings.S3_PROFILE_NAME,
    )
    LOGGER.info("Model %s loaded, version: %s", model_class, settings.MODEL_NAME)
    return model
