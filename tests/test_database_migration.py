from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config


@pytest.mark.integration
def test_alembic_foundation_migration_creates_runtime_tables(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database}")
    try:
        tables = set(inspect(engine).get_table_names())
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
}
