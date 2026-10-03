from pathlib import Path

import pytest

from ai_gif_studio.quality_engine import QualityEngine


class FakeFFmpeg:
    def __init__(self, probe):
        self.probe_data = probe

    async def probe(self, _path: Path, *, count_frames: bool = False):
        assert count_frames is True
        return self.probe_data


def make_probe(width=320, height=320, fps="20/1", duration="6.0", frames=120):
    return {
        "streams": [{
            "codec_type": "video",
            "width": width,
            "height": height,
            "avg_frame_rate": fps,
            "nb_read_frames": frames,
        }],
        "format": {"duration": duration},
    }


@pytest.mark.unit
async def test_quality_gate_accepts_contract_output(tmp_path: Path):
    output = tmp_path / "output.gif"
    output.write_bytes(b"G" * 1000)
    report = await QualityEngine().inspect(
        output, FakeFFmpeg(make_probe()), 2_400_000, selected_fps=20, expected_duration=6.0
    )
    assert report.valid
    assert set(("size", "dimensions", "fps", "duration", "frames")) <= set(report.checks)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("probe", "expected"),
    [(make_probe(fps="10/1"), False), (make_probe(duration="4.0"), False), (make_probe(frames=0), False)],
)
async def test_quality_gate_rejects_invalid_contract(probe, expected, tmp_path: Path):
    output = tmp_path / "output.gif"
    output.write_bytes(b"G" * 1000)
    report = await QualityEngine().inspect(
        output, FakeFFmpeg(probe), 2_400_000, selected_fps=20, expected_duration=6.0
    )
    assert report.valid is expected


@pytest.mark.unit
async def test_quality_gate_accepts_lower_fallback_fps(tmp_path: Path):
    output = tmp_path / "output.gif"
    output.write_bytes(b"G" * 1000)
    report = await QualityEngine().inspect(
        output,
        FakeFFmpeg(make_probe(fps="27/1")),
        2_400_000,
        selected_fps=30,
        accepted_fps=(30, 27, 24, 20, 18, 15),
        expected_duration=6.0,
    )
    assert report.valid
    assert "fps" in report.checks
