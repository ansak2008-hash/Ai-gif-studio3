from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import UUID


class ArtifactStorage:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: UUID) -> Path:
        p = self.root / "jobs" / str(job_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def safe_path(self, job_id: UUID, name: str) -> Path:
        if Path(name).name != name:
            raise ValueError("unsafe filename")
        return self.job_dir(job_id) / name

    def copy_in(self, job_id: UUID, source: str, name: str) -> tuple[Path, int, str]:
        target = self.safe_path(job_id, name)
        shutil.copyfile(source, target)
        h = hashlib.sha256()
        size = 0
        with target.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
                size += len(chunk)
        return target, size, h.hexdigest()
