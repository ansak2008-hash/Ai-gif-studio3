from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_ci_format_gate_rejects_empty_git_revision_paths() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert 'github.event_name' in workflow
    assert 'github.event.pull_request.base.sha' in workflow
    assert 'github.event.before' in workflow
    assert '0000000000000000000000000000000000000000' in workflow
    assert 'git rev-parse --verify "$BASE_SHA^{commit}"' in workflow
    assert 'git diff-tree --root --no-commit-id --name-status -r "${{ github.sha }}"' in workflow
    assert 'git diff --name-status "${{ github.event.pull_request.base.sha }}" "${{ github.sha }}"' not in workflow