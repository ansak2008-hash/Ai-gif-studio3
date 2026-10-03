import pytest

from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings


def test_specs_are_separate_and_versioned():
    d = DesignSpec()
    p = ProcessingSettings()
    assert (
        d.schema_version == 3
        and p.schema_version == 2
        and d.canvas["width"] == 320
        and p.max_bytes == 2400000
    )


def test_processing_settings_reject_output_limit_above_hard_contract() -> None:
    with pytest.raises(ValueError, match="less than or equal to 2400000"):
        ProcessingSettings(max_bytes=2_400_001)
