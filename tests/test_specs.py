from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings


def test_specs_are_separate_and_versioned():
    d = DesignSpec()
    p = ProcessingSettings()
    assert d.schema_version == 3
    assert p.schema_version == 2
    assert d.canvas["width"] == 320
    assert p.max_bytes == 2400000
