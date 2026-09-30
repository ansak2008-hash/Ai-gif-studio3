from __future__ import annotations

import pytest

from ai_gif_studio.database.tables import AIExecutionRecord, ArtifactRecord


@pytest.mark.unit
def test_database_records_import_and_preserve_metadata_column_name() -> None:
    assert ArtifactRecord.__table__.c.metadata.name == "metadata"
    assert AIExecutionRecord.__table__.c.metadata.name == "metadata"
    assert "metadata_json" in ArtifactRecord.__mapper__.attrs
    assert "metadata_json" in AIExecutionRecord.__mapper__.attrs
    assert "metadata" not in ArtifactRecord.__mapper__.attrs
    assert "metadata" not in AIExecutionRecord.__mapper__.attrs
