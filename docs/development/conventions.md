# Development Conventions

## Python Imports and Ruff I001

Ruff's I001 is the import-sorting rule inherited from isort. Do **not** treat a blank line after the import block as inherently invalid.

The canonical module layout is:

1. future import, when required;
2. standard-library imports;
3. third-party imports;
4. first-party imports;
5. a blank line separating imports from executable/module-level declarations;
6. module-level declarations and then definitions.

Example:

    from __future__ import annotations

    import numpy as np
    import pytest

    from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

    pytestmark = pytest.mark.unit

A module-level declaration such as pytestmark is **not** part of the import block merely because it follows imports. If Ruff reports I001, use Ruff's diagnostic/fix output to identify the actual import-order or spacing issue rather than deleting the required separator blindly.

## Formatting Policy

- Ruff is the source of truth for import sorting and formatting.
- Prefer "ruff check . --fix" for safe automated lint fixes.
- Run "ruff format ." when formatting changes are intended.
- Do not introduce manual formatting rules that contradict Ruff.
- CI remains authoritative; never claim a lint fix passed without observing the CI result.

## Pre-commit

The repository uses Ruff through pre-commit to catch import and formatting problems before they reach CI.

Install once:

    pre-commit install

Run manually when needed:

    pre-commit run --all-files
