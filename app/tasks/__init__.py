"""Package with Celery's tasks implementation."""
from app.tasks.predict import predict

__all__ = ["predict"]
