from sqlalchemy import create_engine, inspect, text

from app.db import initialize_database


def test_initialize_database_adds_agent_key_to_existing_runs_table() -> None:
    legacy_engine = create_engine("sqlite+pysqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE workflow_runs (
                    id VARCHAR(36) PRIMARY KEY,
                    title VARCHAR(160) NOT NULL,
                    prompt TEXT NOT NULL,
                    state VARCHAR(32) NOT NULL,
                    attempt INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    total_cost_usd NUMERIC(12, 4) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )

    initialize_database(legacy_engine)

    columns = {column["name"] for column in inspect(legacy_engine).get_columns("workflow_runs")}
    assert "agent_key" in columns
