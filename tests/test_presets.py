from ai_gif_studio.engines.presets import build_design_spec, list_presets


def test_design_presets_are_deterministic_and_bounded():
    names = list_presets()
    assert len(names) == 8
    for name in names:
        spec = build_design_spec(name)
        assert spec.schema_version == 3
        assert spec.canvas == {"width": 320, "height": 320}


def test_preset_overrides_are_allowlisted():
    spec = build_design_spec("luxury_gold", {"typography": {"content": "محمد", "size": 72}})
    assert spec.typography["content"] == "محمد"
    try:
        build_design_spec("luxury_gold", {"__class__": {"x": "y"}})
    except ValueError as exc:
        assert "unsupported preset override section" in str(exc)
    else:
        raise AssertionError("unsafe preset section was accepted")
