from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db import get_session as app_get_session


@pytest.fixture
def engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient

    from app.main import app

    Base.metadata.create_all(engine)

    def override_session():
        with Session(engine) as db_session:
            yield db_session

    app.dependency_overrides[app_get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
