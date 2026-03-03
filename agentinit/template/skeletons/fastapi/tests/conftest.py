import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("TODOS_DB_PATH", str(db_path))
    with TestClient(app) as test_client:
        yield test_client
