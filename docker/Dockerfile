FROM python:3.10.6-slim AS base

RUN apt-get update && apt-get install -y curl
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
ENV PATH="$PATH:/etc/poetry/bin"

COPY pyproject.toml pyproject.toml
RUN poetry install --no-root --only main

WORKDIR /app
COPY /playlist_selection /playlist_selection
# TODO: fix, build and install
ENV PYTHONPATH "${PYTHONPATH}:/"

EXPOSE 5000

ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY /app /app

FROM base AS test

WORKDIR /test_root
RUN poetry run pip install pytest pytest-cov
