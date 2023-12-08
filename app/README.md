* FastAPI

Run redis:

```bash
docker run -p 6379:6379 -it redis/redis-stack:latest
```

Run FastAPI with:

```bash
poetry run python -m uvicorn main:app --reload --port 5000
```

* Flask:

TBD