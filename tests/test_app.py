import sys
sys.path.append("/home/slava/playlist_selection/app")

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

@pytest.fixture()
def client():
    from app.main import app
    from app.main import auth_dependency

    with TestClient(app) as test_client:
        auth_mock = MagicMock()
        auth_mock.get_spotipy = MagicMock(return_value=None)
        app.dependency_overrides[auth_dependency] = auth_mock
        yield test_client

ENVS = ["REDIS_HOST", "REDIS_PORT", "REDIS_DB"]
for env in ENVS:
    import os
    os.environ[env] = ""

@patch("redis.Redis")
def test_app_simple(mock_redis, client):
    response = client.get("/")
    assert response.status_code == 200
