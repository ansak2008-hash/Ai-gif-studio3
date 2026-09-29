from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from ai_gif_studio.domain.persistence import (
    PersistenceValidationError,
    RevisionGraphPersistence,
)
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.revisions import Revision
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.infrastructure.persistence import (
    FilesystemPersistence,
    PersistenceStorageError,
)


def _document(marker: str = "root") -> str:
    root = Revision.create(
        ProjectState(
            uuid4(),
            0,
            DesignSpec(),
            ProcessingSettings(),
            {"marker": marker},
        ),
        None,
        {"command": marker},
    )
    from ai_gif_studio.domain.revisions import RevisionGraph

    return RevisionGraphPersistence.encode(RevisionGraph(root))


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    adapter = FilesystemPersistence(tmp_path / "project.json")
    document = _document()
    adapter.save(document)
    assert adapter.load() == document


def test_save_rejects_non_canonical_document_before_mutation(tmp_path: Path) -> None:
    primary = tmp_path / "project.json"
    adapter = FilesystemPersistence(primary)
    with pytest.raises(PersistenceValidationError):
        adapter.save("{}")
    assert not primary.exists()


def test_replacement_failure_preserves_previous_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = tmp_path / "project.json"
    adapter = FilesystemPersistence(primary)
    old = _document("old")
    adapter.save(old)
    new = _document("new")

    def fail_replace(source: Path, target: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("ai_gif_studio.infrastructure.persistence.os.replace", fail_replace)
    with pytest.raises(PersistenceStorageError):
        adapter.save(new)
    assert primary.read_text(encoding="utf-8") == old
    assert not list(tmp_path.glob("project.json.tmp-*"))


def test_temporary_write_failure_is_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = tmp_path / "project.json"
    adapter = FilesystemPersistence(primary)
    document = _document()

    class FailingFile:
        def __enter__(self) -> FailingFile:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def write(self, value: str) -> int:
            raise OSError("write failed")

    monkeypatch.setattr(
        "ai_gif_studio.infrastructure.persistence.tempfile.NamedTemporaryFile",
        lambda *args, **kwargs: FailingFile(),
    )
    with pytest.raises(PersistenceStorageError):
        adapter.save(document)
    assert not list(tmp_path.glob("project.json.tmp-*"))


def test_flush_failure_does_not_report_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = FilesystemPersistence(tmp_path / "project.json")
    document = _document()

    class FlushFail:
        def __enter__(self) -> FlushFail:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def write(self, value: str) -> int:
            return len(value)

        def flush(self) -> None:
            raise OSError("flush failed")

        def fileno(self) -> int:
            return 1

    monkeypatch.setattr(
        "ai_gif_studio.infrastructure.persistence.tempfile.NamedTemporaryFile",
        lambda *args, **kwargs: FlushFail(),
    )
    with pytest.raises(PersistenceStorageError):
        adapter.save(document)


def test_valid_recovery_candidate_is_promoted(tmp_path: Path) -> None:
    primary = tmp_path / "project.json"
    recovery = tmp_path / "project.json.recovery"
    adapter = FilesystemPersistence(primary)
    document = _document("recovery")
    recovery.write_text(document, encoding="utf-8")
    assert adapter.load() == document
    assert primary.read_text(encoding="utf-8") == document


def test_invalid_recovery_candidate_fails_closed(tmp_path: Path) -> None:
    adapter = FilesystemPersistence(tmp_path / "project.json")
    (tmp_path / "project.json.recovery").write_text("{}", encoding="utf-8")
    with pytest.raises(PersistenceStorageError):
        adapter.load()


def test_valid_primary_wins_over_invalid_recovery(tmp_path: Path) -> None:
    primary = tmp_path / "project.json"
    adapter = FilesystemPersistence(primary)
    document = _document("primary")
    adapter.save(document)
    (tmp_path / "project.json.recovery").write_text("{}", encoding="utf-8")
    assert adapter.load() == document


def test_corrupted_primary_with_valid_recovery_is_recovered(tmp_path: Path) -> None:
    primary = tmp_path / "project.json"
    recovery = tmp_path / "project.json.recovery"
    adapter = FilesystemPersistence(primary)
    document = _document("recovery")
    primary.write_text("corrupted", encoding="utf-8")
    recovery.write_text(document, encoding="utf-8")
    assert adapter.load() == document
    assert primary.read_text(encoding="utf-8") == document


def test_corrupted_primary_and_recovery_fail_closed(tmp_path: Path) -> None:
    primary = tmp_path / "project.json"
    adapter = FilesystemPersistence(primary)
    primary.write_text("bad", encoding="utf-8")
    (tmp_path / "project.json.recovery").write_text("also bad", encoding="utf-8")
    with pytest.raises(PersistenceStorageError):
        adapter.load()


def test_noncanonical_recovery_is_rejected(tmp_path: Path) -> None:
    adapter = FilesystemPersistence(tmp_path / "project.json")
    canonical = _document()
    payload = json.loads(canonical)
    recovery = tmp_path / "project.json.recovery"
    recovery.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with pytest.raises(PersistenceStorageError):
        adapter.load()


def test_recovery_does_not_remove_unrelated_files(tmp_path: Path) -> None:
    adapter = FilesystemPersistence(tmp_path / "project.json")
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("keep", encoding="utf-8")
    (tmp_path / "project.json.recovery").write_text(_document(), encoding="utf-8")
    adapter.load()
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_path_is_scoped_to_primary_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    adapter = FilesystemPersistence(tmp_path / "nested" / "project.json")
    assert adapter.recovery_path.parent == tmp_path / "nested"
    assert adapter.recovery_path != outside / "project.json.recovery"


def test_phase54_decode_remains_the_integrity_gate(tmp_path: Path) -> None:
    adapter = FilesystemPersistence(tmp_path / "project.json")
    document = _document()
    adapter.save(document)
    assert RevisionGraphPersistence.encode(RevisionGraphPersistence.decode(adapter.load())) == document
