"""Celery app configuration."""
import os

from celery import Celery

app = Celery(
    "tasks",
    broker=f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}/0"
)
