from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGETS = {
    "src/ai_gif_studio/quality_engine/engine.py": 0,
    "src/ai_gif_studio/infrastructure/ffmpeg.py": 0,
    "src/ai_gif_studio/engines/validator.py": 0,
    "src/ai_gif_studio/infrastructure/worker.py": 1,
    "src/ai_gif_studio/infrastructure/recovery.py": 0,
}


def handler_kind(node: ast.ExceptHandler) -> str:
    if node.type is None:
        return "bare-except"
    if isinstance(node.type, ast.Name):
        return node.type.id
    if isinstance(node.type, ast.Tuple):
        return ",".join(
            element.id if isinstance(element, ast.Name) else ast.unparse(element)
            for element in node.type.elts
        )
    return ast.unparse(node.type)


def main() -> int:
    violations = []
    for rel, allowed in TARGETS.items():
        path = Path(rel)
        if not path.exists():
            violations.append(f"{rel}: file not found")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = [
            (node.lineno, handler_kind(node))
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and (
                node.type is None
                or any(broad in handler_kind(node) for broad in {"Exception", "BaseException"})
            )
        ]
        if len(found) > allowed:
            for line, kind in found:
                violations.append(f"{rel}:{line} broad handler: {kind}")

    if violations:
        print("Broad exception handlers beyond allowance:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    print("Exception handling audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
