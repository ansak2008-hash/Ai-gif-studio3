from ai_gif_studio.domain.specs import DesignSpec,ProcessingSettings
def test_specs_are_separate_and_versioned():
    d=DesignSpec(); p=ProcessingSettings()
    assert d.schema_version==2 and p.schema_version==2 and d.canvas["width"]==320 and p.max_bytes==2400000
