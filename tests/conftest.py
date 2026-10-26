import pytest
from fastapi.testclient import TestClient
from app.main import create_app
@pytest.fixture
def app(tmp_path):
    return create_app(f'sqlite:///{tmp_path}/test.db', reminders_enabled=False)
@pytest.fixture
def client(app):
    with TestClient(app) as c: yield c
@pytest.fixture
def session(app):
    with app.state.session_factory() as s: yield s
