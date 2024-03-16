"""Celery app configuration."""
import os

from celery import Celery

app = Celery(
    "tasks",
    broker=f"redis://{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}/0"
)

# TODO: remove pickle dependency
app.conf.event_serializer = "pickle"
app.conf.task_serializer = "pickle"
app.conf.result_serializer = "json"
app.conf.accept_content = ['application/json', 'application/x-python-serialize']
