from __future__ import annotations

import errno
import os
import tempfile
from pathlib import Path

from ai_gif_studio.domain.persistence import RevisionGraphPersistence, PersistenceValidationError


class PersistenceStorageError(RuntimeError):
    """Raised when filesystem persistence cannot complete safely."""


def _sync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(directory, flags)
    except OSError as exc:
        if exc.errno in {errno.EINVAL, errno.ENOTSUP, errno.EISDIR}:
            return
        raise
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class FilesystemPersistence:
    """Crash-safe local filesystem adapter for canonical persistence documents."""

    def __init__(self, primary_path: Path) -> None:
        self.primary_path = Path(primary_path)
        self.recovery_path = self.primary_path.with_name(
            f"{self.primary_path.name}.recovery"
        )

    def save(self, document: str) -> None:
        if not isinstance(document, str):
            raise TypeError("document must be a string")
        try:
            RevisionGraphPersistence.decode(document)
        except PersistenceValidationError:
            raise

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.primary_path.parent,
                prefix=f"{self.primary_path.name}.tmp-",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(document)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary_path, self.primary_path)
            temporary_path = None
            _sync_directory(self.primary_path.parent)
        except OSError as exc:
            raise PersistenceStorageError("crash-safe persistence failed") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

    def load(self) -> str:
        try:
            primary = self._read_valid(self.primary_path)
        except FileNotFoundError:
            primary = None
        except PersistenceStorageError:
            raise

        if primary is not None:
            return primary

        try:
            recovery = self._read_valid(self.recovery_path)
        except FileNotFoundError as exc:
            raise PersistenceStorageError("no valid persisted document is available") from exc

        try:
            self.save(recovery)
        except (PersistenceValidationError, PersistenceStorageError) as exc:
            raise PersistenceStorageError("valid recovery could not be promoted") from exc
        return recovery

    @staticmethod
    def _read_valid(path: Path) -> str:
        try:
            document = path.read_text(encoding="utf-8")
        except OSError as exc:
            if isinstance(exc, FileNotFoundError):
                raise
            raise PersistenceStorageError("persisted document could not be read") from exc

        try:
            RevisionGraphPersistence.decode(document)
        except PersistenceValidationError as exc:
            raise PersistenceStorageError("persisted document failed integrity validation") from exc
        return document
