FROM python:3.10.6-slim

RUN apt-get update && apt-get install -y curl
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
ENV PATH="$PATH:/etc/poetry/bin"

COPY pyproject.toml pyproject.toml
RUN poetry install --no-root --without dev,test

WORKDIR /app
COPY /src /src

EXPOSE 8000

ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# for fast rebuild
COPY /app /app
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
