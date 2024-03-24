"""Celery app configuration."""
from celery import Celery

from app.config import get_settings

settings = get_settings()

app = Celery(
    "tasks",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    include=["app.tasks"],
)

# TODO: remove pickle dependency
app.conf.event_serializer = "pickle"
app.conf.task_serializer = "pickle"
app.conf.result_serializer = "json"
app.conf.accept_content = ['application/json', 'application/x-python-serialize']
