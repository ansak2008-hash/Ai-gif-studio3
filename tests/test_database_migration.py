from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


@pytest.mark.integration
def test_alembic_foundation_migration_creates_runtime_tables(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database}")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        constraints = inspector.get_unique_constraints("artifacts")
    finally:
        engine.dispose()

    expected = {
        "alembic_version",
        "processing_jobs",
        "artifacts",
        "job_steps",
        "design_specs",
        "processing_settings",
        "ai_executions",
        "models",
        "workflows",
    }
    assert expected <= tables
    assert any(
        constraint["name"] == "uq_artifacts_identity"
        and constraint["column_names"] == ["job_id", "type", "storage_path"]
        for constraint in constraints
    )
