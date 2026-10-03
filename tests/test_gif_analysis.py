from __future__ import annotations

import io
import json

import numpy as np
import pytest
from PIL import Image

from ai_gif_studio.application.gif_analysis import (
    GifAnalysisError,
    GifAnalysisReport,
    analyze_gif_bytes,
    analyze_gif_url,
)


def make_gif(
    *,
    durations: list[int],
    colors: list[tuple[int, int, int]],
) -> bytes:
    frames = [Image.new("RGB", (4, 4), color) for color in colors]
    output = io.BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
    )
    return output.getvalue()


def test_analysis_reports_dimensions_duration_fps_and_size() -> None:
    payload = make_gif(
        durations=[100, 200],
        colors=[(0, 0, 0), (255, 0, 0)],
    )
    report = analyze_gif_bytes(payload)
    assert isinstance(report, GifAnalysisReport)
    assert report.width == 4
    assert report.height == 4
    assert report.frame_count == 2
    assert report.duration_ms == 300
    assert report.effective_fps == pytest.approx(6.6666667)
    assert report.file_size_bytes == len(payload)
    assert report.loop_count == 0


def test_analysis_is_deterministic_and_json_serializable() -> None:
    payload = make_gif(
        durations=[100, 100],
        colors=[(10, 20, 30), (40, 50, 60)],
    )
    first = analyze_gif_bytes(payload)
    second = analyze_gif_bytes(payload)
    assert first == second
    assert first.to_json() == second.to_json()
    assert json.loads(first.to_json())["schema_version"] == 1


def test_motion_statistics_and_percentiles_are_reported() -> None:
    payload = make_gif(
        durations=[100, 100, 100],
        colors=[(0, 0, 0), (255, 0, 0), (255, 255, 0)],
    )
    report = analyze_gif_bytes(payload)
    assert report.motion_mean > 0
    assert report.motion_max >= report.motion_mean
    assert report.frame_motion[0] > 0
    assert report.frame_motion[1] > 0
    assert report.first_last_difference > 0
    assert report.motion_p25 > 0
    assert report.motion_p50 > 0
    assert report.motion_p75 > 0
    assert report.motion_p90 > 0
    assert report.motion_p95 > 0
    assert report.motion_p99 > 0


def test_corner_background_is_explicitly_a_heuristic() -> None:
    payload = make_gif(durations=[100], colors=[(1, 2, 3)])
    report = analyze_gif_bytes(payload)
    assert report.corner_color == (1, 2, 3)
    assert report.corner_color_is_heuristic is True


def test_palette_cardinality_and_timing_histogram_are_reported() -> None:
    payload = make_gif(
        durations=[100, 200, 100],
        colors=[(0, 0, 0), (255, 0, 0), (0, 255, 0)],
    )
    report = analyze_gif_bytes(payload)
    assert report.frame_palette_colors == (1, 1, 1)
    assert report.max_palette_colors == 1
    assert report.duration_min_ms == 100
    assert report.duration_max_ms == 200
    assert report.duration_histogram == ((100, 2), (200, 1))
    assert report.timing_is_uniform is False


def test_invalid_and_empty_input_fail_closed() -> None:
    with pytest.raises(GifAnalysisError):
        analyze_gif_bytes(b"")
    with pytest.raises(GifAnalysisError):
        analyze_gif_bytes(b"not a gif")


def test_input_and_resource_limits_are_enforced() -> None:
    payload = make_gif(durations=[100], colors=[(0, 0, 0)])
    with pytest.raises(GifAnalysisError, match="input exceeds"):
        analyze_gif_bytes(payload, max_input_bytes=len(payload) - 1)
    with pytest.raises(GifAnalysisError, match="canvas"):
        analyze_gif_bytes(payload, max_canvas_pixels=1)
    with pytest.raises(GifAnalysisError, match="frame limit"):
        analyze_gif_bytes(
            make_gif(durations=[100, 100], colors=[(0, 0, 0), (1, 1, 1)]),
            max_decoded_frames=1,
        )
    with pytest.raises(GifAnalysisError, match="pixel budget"):
        analyze_gif_bytes(payload, max_total_pixels=1)
    with pytest.raises(GifAnalysisError, match="limits"):
        analyze_gif_bytes(payload, max_input_bytes=0)


def test_truncated_gif_fails_closed() -> None:
    payload = make_gif(
        durations=[100, 100],
        colors=[(0, 0, 0), (255, 255, 255)],
    )
    with pytest.raises(GifAnalysisError):
        analyze_gif_bytes(payload[: len(payload) // 2])


def test_source_bytes_are_not_mutated() -> None:
    payload = make_gif(durations=[100], colors=[(0, 0, 0)])
    original = bytes(payload)
    analyze_gif_bytes(payload)
    assert payload == original


def test_url_adapter_rejects_invalid_limits_and_over_limit_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = make_gif(durations=[100], colors=[(0, 0, 0)])

    class Headers:
        def get(self, name: str) -> str | None:
            return str(len(payload) + 1) if name == "Content-Length" else None

    class FakeResponse:
        headers = Headers()

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, limit: int = -1) -> bytes:
            return payload

    monkeypatch.setattr(
        "ai_gif_studio.application.gif_analysis.urlopen",
        lambda request, timeout: FakeResponse(),
    )
    with pytest.raises(GifAnalysisError, match="response exceeds"):
        analyze_gif_url("https://example.test/reference.gif", max_input_bytes=len(payload))
    with pytest.raises(GifAnalysisError, match="limits"):
        analyze_gif_url("https://example.test/reference.gif", max_input_bytes=0)


def test_url_adapter_uses_bounded_chunk_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = make_gif(durations=[100], colors=[(0, 0, 0)])
    requested: list[int] = []

    class Headers:
        def get(self, name: str) -> str | None:
            return None

    class FakeResponse:
        headers = Headers()

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, limit: int = -1) -> bytes:
            requested.append(limit)
            return payload[:limit]

    monkeypatch.setattr(
        "ai_gif_studio.application.gif_analysis.urlopen",
        lambda request, timeout: FakeResponse(),
    )
    report = analyze_gif_url("https://example.test/reference.gif", max_input_bytes=len(payload))
    assert report.frame_count == 1
    assert requested
    assert all(limit <= 64 * 1024 for limit in requested)


def test_url_adapter_rejects_invalid_url() -> None:
    with pytest.raises(GifAnalysisError, match="HTTP or HTTPS"):
        analyze_gif_url("file:///tmp/reference.gif")


def test_report_does_not_contain_frame_arrays() -> None:
    payload = make_gif(durations=[100], colors=[(0, 0, 0)])
    report = analyze_gif_bytes(payload)
    assert not any(isinstance(value, np.ndarray) for value in report.__dict__.values())


def test_zero_frame_delay_fails_closed() -> None:
    payload = bytearray(make_gif(durations=[100], colors=[(0, 0, 0)]))
    marker = payload.find(b"\\x21\\xf9\\x04")
    assert marker >= 0
    payload[marker + 4] = 0
    payload[marker + 5] = 0
    with pytest.raises(GifAnalysisError, match="duration must be positive"):
        analyze_gif_bytes(bytes(payload))


def test_decoded_frame_and_pixel_limits_fail_before_unbounded_accumulation() -> None:
    payload = make_gif(
        durations=[100, 100, 100],
        colors=[(0, 0, 0), (1, 1, 1), (2, 2, 2)],
    )
    with pytest.raises(GifAnalysisError, match="frame limit"):
        analyze_gif_bytes(payload, max_decoded_frames=2)
    with pytest.raises(GifAnalysisError, match="pixel budget"):
        analyze_gif_bytes(payload, max_total_pixels=16 * 2)


def test_exact_input_byte_boundary_is_authoritative() -> None:
    payload = make_gif(durations=[100], colors=[(0, 0, 0)])
    analyze_gif_bytes(payload, max_input_bytes=len(payload))
    with pytest.raises(GifAnalysisError, match="input exceeds"):
        analyze_gif_bytes(payload, max_input_bytes=len(payload) - 1)
