from pathlib import Path

import pytest

from ai_gif_studio.engines.debug_trace import DebugTraceBundle


@pytest.mark.unit
def test_debug_trace_bundle_writes_failure_diagnostics_without_media(tmp_path: Path) -> None:
    target = tmp_path / "result.gif"
    bundle = DebugTraceBundle().record_failure(
        target=target,
        error=ValueError("render failed"),
        probe={"streams": [{"codec_type": "video", "width": 320}]},
        filtergraph="[0:v]null[out]",
        metadata={"stage": "render"},
    )

    assert bundle.is_dir()
    assert (bundle / "manifest.json").is_file()
    assert (bundle / "error.txt").read_text(encoding="utf-8").startswith("ValueError:")
    assert (bundle / "probe.json").is_file()
    assert (bundle / "filtergraph.txt").read_text(encoding="utf-8") == "[0:v]null[out]"
    assert not (bundle / "result.gif").exists()
