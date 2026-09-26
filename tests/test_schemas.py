import pytest

from ai_gif_studio.schemas import DesignSpec, ProcessingSettings


def test_design_spec_defaults_to_320_square_canvas() -> None:
    spec = DesignSpec.from_payload({})
    assert (spec.canvas.width, spec.canvas.height) == (320, 320)
    assert spec.schema_version == 1


def test_processing_settings_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unsupported ProcessingSettings"):
        ProcessingSettings.from_payload({"schema_version": 99})
