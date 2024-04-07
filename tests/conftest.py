import pytest
import os

def pytest_addoption(parser):
    parser.addoption(
        "--skip-slow", action="store_true", default=False, help="skip slow tests"
    )
    parser.addoption(
        "--skip-integration", action="store_true", default=False, help="skip slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "integration_test: mark test as integration")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--skip-slow"):
        skip_slow = pytest.mark.skip(reason="you need to remove --skip-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if config.getoption("--skip-integration"):
        skip_integration = pytest.mark.skip(reason="you need to remove --skip-integration option to run")
        for item in items:
            if "integration_test" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    print("SETUP ENV")

    os.environ["PLAYLIST_SELECTION_CLIENT_ID"] = ""
    os.environ["PLAYLIST_SELECTION_CLIENT_SECRET"] = ""
    os.environ["PLAYLIST_SELECTION_CALLBACK_URL"] = "https://localhost:5000"
    os.environ["PLAYLIST_SELECTION_S3_ENDPOINT_URL"] = "https://minio"
    os.environ["PLAYLIST_SELECTION_S3_BUCKET_NAME"] = ""
    os.environ["PLAYLIST_SELECTION_S3_PROFILE_NAME"] = ""
    os.environ["PLAYLIST_SELECTION_MODEL_CLASS"] = ""
    os.environ["PLAYLIST_SELECTION_MODEL_NAME"] = ""

    os.environ["PLAYLIST_SELECTION_PGUSER"] = "user"
    os.environ["PLAYLIST_SELECTION_PGPASSWORD"] = "past"
    os.environ["PLAYLIST_SELECTION_PGHOST"] = "test-db"
    os.environ["PLAYLIST_SELECTION_PGPORT"] = "5932"
    os.environ["PLAYLIST_SELECTION_PGDATABASE"] = "playlist_selection"
    os.environ["PLAYLIST_SELECTION_PGSSLMODE"] = "allow"
    # os.environ["PLAYLIST_SELECTION_PGSSLROOTCERT"] = ""

    os.environ["PLAYLIST_SELECTION_REDIS_HOST"] = "redis"
    os.environ["PLAYLIST_SELECTION_REDIS_PORT"] = "6379"
    # os.environ["AWS_ACCESS_KEY_ID"]
    # os.environ["AWS_SECRET_ACCESS_KEY"]
    # os.environ["AWS_DEFAULT_REGION"]
    # os.environ["AWS_ENDPOINT_URL"]
