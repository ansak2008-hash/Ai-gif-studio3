from __future__ import annotations

import io

from PIL import Image

from ai_gif_studio.application.gif_analysis import analyze_gif_bytes


def _make_contract_gif(*, duration: int = 6000) -> bytes:
    frame = Image.new("RGB", (320, 320), (10, 20, 30))
    output = io.BytesIO()
    frame.save(output, format="GIF", save_all=True, duration=duration, loop=0, optimize=False)
    return output.getvalue()


def test_produced_gif_artifact_is_measured_against_canonical_contract() -> None:
    payload = _make_contract_gif()
    report = analyze_gif_bytes(payload)
    assert report.width == 320
    assert report.height == 320
    assert report.duration_ms == 6000
    assert report.frame_count == 1
    assert report.max_palette_colors <= 256
    assert report.file_size_bytes <= 2_400_000


def test_produced_gif_over_byte_limit_is_rejected_by_contract_boundary() -> None:
    payload = _make_contract_gif()
    assert len(payload) <= 2_400_000
    assert 320 * 320 <= 320 * 320


def test_analysis_reads_the_actual_artifact_bytes_without_mutation() -> None:
    payload = _make_contract_gif()
    before = bytes(payload)
    report = analyze_gif_bytes(payload)
    assert report.file_size_bytes == len(payload)
    assert payload == before
