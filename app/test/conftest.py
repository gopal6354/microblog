import os
import tempfile
from pathlib import Path

# settings are read at import time, so configure a throwaway environment first
_db_file = Path(tempfile.mkdtemp()) / "test.db"
os.environ.update(
    {
        "SECRET_KEY": "test-secret",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_TIME": "1",
        "REFRESH_TOKEN_EXPIRE_TIME": "7",
        "DATABASE_URL": f"sqlite:///{_db_file}",
        "EMAIL_HOST": "localhost",
        "EMAIL_PORT": "465",
        "EMAIL_ADDRESS": "test@example.com",
        "EMAIL_PASSWORD": "test",
        "SENTRY_DSN": "",
        "SENTRY_ENVIRONMENT": "test",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import Base, Session, engine  # noqa: E402
from models.user import User, RoleChoice, StatusChoice  # noqa: E402
from utils import email_service  # noqa: E402
from utils.security import hash_password  # noqa: E402


PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def db(monkeypatch):
    monkeypatch.setattr(email_service, "send_email", lambda *args, **kwargs: None)
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(main.app, follow_redirects=False)


@pytest.fixture
def make_user(db):
    def _make_user(username, role=RoleChoice.USER, **fields):
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=hash_password(PASSWORD),
            role=role,
            status=StatusChoice.ACTIVE,
            otp_verified=True,
            **fields,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make_user


def login(client, username, password=PASSWORD):
    return client.post("/login", data={"username": username, "password": password})
