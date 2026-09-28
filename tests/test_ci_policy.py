import tomllib
from pathlib import Path


def test_ruff_has_explicit_strict_rules():
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lint = config["tool"]["ruff"]["lint"]
    assert lint["select"] == ["F", "E", "W", "I", "UP", "B"]


def test_no_ruff_exclude_escape_hatch():
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lint = config["tool"]["ruff"]["lint"]
    assert "extend-exclude" not in lint
    assert "exclude" not in lint


def test_phase_two_unit_markers_present():
    for name in (
        "test_perspective_camera.py",
        "test_depth_field.py",
        "test_temporal_engine.py",
    ):
        content = Path("tests", name).read_text(encoding="utf-8")
        assert "pytest.mark.unit" in content, name
