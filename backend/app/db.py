from collections.abc import Generator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


DATABASE_URL = get_settings().database_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database(database_engine: Engine = engine) -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(database_engine)
    inspector = inspect(database_engine)
    if "workflow_runs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("workflow_runs")}
    if "agent_key" not in columns:
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE workflow_runs ADD COLUMN agent_key VARCHAR(64) "
                    "NOT NULL DEFAULT 'incident_response'"
                )
            )


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
