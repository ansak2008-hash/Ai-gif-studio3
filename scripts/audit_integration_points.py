from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UTF8_FILES = (
    "src/ai_gif_studio/domain/project.py",
    "src/ai_gif_studio/domain/revisions.py",
    "src/ai_gif_studio/domain/specs.py",
    "src/ai_gif_studio/domain/persistence.py",
)
QUEUE_FILES = (
    "src/ai_gif_studio/telegram/router.py",
    "src/ai_gif_studio/infrastructure/worker.py",
    "src/ai_gif_studio/worker.py",
)


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _has_import(path: str, module_fragment: str) -> bool:
    tree = ast.parse(_source(path), filename=path)
    return any(
        isinstance(node, ast.ImportFrom) and module_fragment in node.module
        for node in ast.walk(tree)
    )


def check_utf8_validator_usage() -> bool:
    ok = True
    for path in UTF8_FILES:
        source = _source(path)
        if not _has_import(path, "canonical_validation") or "validate_" not in source:
            print(f"FAIL: {path}: missing canonical UTF-8 validation integration")
            ok = False
    if ok:
        print("PASS: UTF-8 validator integrated at canonical boundaries")
    return ok


def check_atomic_queue_usage() -> bool:
    ok = True
    for path in QUEUE_FILES:
        source = _source(path)
        if "AtomicJobQueue" not in source:
            print(f"FAIL: {path}: missing AtomicJobQueue integration")
            ok = False
    worker_sources = (_source(path) for path in QUEUE_FILES if "worker.py" in path)
    if not any("claim_for_processing" in source for source in worker_sources):
        print("FAIL: no worker path uses claim_for_processing")
        ok = False
    if ok:
        print("PASS: AtomicJobQueue integrated at enqueue/worker boundaries")
    return ok


def main() -> int:
    return 0 if check_utf8_validator_usage() and check_atomic_queue_usage() else 1


if __name__ == "__main__":
    sys.exit(main())
