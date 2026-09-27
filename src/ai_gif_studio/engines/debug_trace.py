from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class DebugTraceBundle:
    """Persist failure diagnostics without copying source media or intermediates."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root

    def record_failure(
        self,
        *,
        target: Path,
        error: BaseException,
        probe: dict[str, Any] | None = None,
        filtergraph: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        base = self.root or target.parent / "debug-traces"
        bundle = base / f"{target.stem}-{stamp}"
        bundle.mkdir(parents=True, exist_ok=True)

        manifest = {
            "schema_version": 1,
            "created_at": stamp,
            "target": target.name,
            "error_type": type(error).__name__,
            "error": str(error),
            "metadata": metadata or {},
            "files": ["manifest.json", "error.txt"],
        }
        (bundle / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (bundle / "error.txt").write_text(
            f"{type(error).__name__}: {error}\n",
            encoding="utf-8",
        )

        if probe is not None:
            (bundle / "probe.json").write_text(
                json.dumps(probe, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            manifest["files"].append("probe.json")

        if filtergraph:
            (bundle / "filtergraph.txt").write_text(filtergraph, encoding="utf-8")
            manifest["files"].append("filtergraph.txt")

        (bundle / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return bundle
