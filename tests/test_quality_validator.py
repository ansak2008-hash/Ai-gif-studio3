from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from ai_gif_studio.application.gif_analysis import GifAnalysisError
from ai_gif_studio.domain.probe_errors import ProbeExecutionError
from ai_gif_studio.engines.validator import OutputValidator, preflight_gif_budget
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService


def test_rejects_missing_and_wrong_magic(tmp_path: Path):
    p = tmp_path / "x.gif"
    p.write_bytes(b"notgif")
    assert not OutputValidator().validate_basic_gif(p, 100)


def test_rejects_empty_and_oversized_gif(tmp_path: Path):
    empty = tmp_path / "empty.gif"
    empty.write_bytes(b"")
    oversized = tmp_path / "large.gif"
    oversized.write_bytes(b"GIF89a" + b"x" * 100)
    validator = OutputValidator()
    assert not validator.validate_basic_gif(empty, 100)
    assert not validator.validate_basic_gif(oversized, 10)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validates_real_gif_geometry(tmp_path: Path):
    src = tmp_path / "in.mp4"
    out = tmp_path / "out.gif"
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg unavailable")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x320:rate=8",
            "-t",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(src),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(src),
            "-vf",
            "fps=8,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse",
            str(out),
        ],
        check=True,
    )
    validator = OutputValidator(FFmpegService(timeout=30))
    assert await validator.validate_gif(
        out,
        2_400_000,
        expected_fps=8,
        expected_duration=1.0,
        duration_tolerance=0.35,
    )


class _Probe:
    async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
        return {
            "format": {"duration": "1.0"},
            "streams": [
                {
                    "codec_type": "video",
                    "width": 320,
                    "height": 320,
                    "avg_frame_rate": "2/1",
                    "nb_read_frames": "2",
                }
            ],
        }


class _ProbeRaiser:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
        raise self.error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_contains_only_classified_probe_errors(tmp_path: Path) -> None:
    path = tmp_path / "output.gif"
    path.write_bytes(b"GIF89a")
    validator = OutputValidator()
    assert not await validator.validate_gif(
        path,
        100,
        ffmpeg=_ProbeRaiser(ProbeExecutionError("corrupt media")),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_does_not_translate_internal_value_error(tmp_path: Path) -> None:
    path = tmp_path / "output.gif"
    path.write_bytes(b"GIF89a")
    validator = OutputValidator()
    with pytest.raises(ValueError, match="internal bug"):
        await validator.validate_gif(
            path,
            100,
            ffmpeg=_ProbeRaiser(ValueError("internal bug")),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_enforces_decoded_artifact_contract(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    frames = [Image.new("RGB", (320, 320), color) for color in ((10, 20, 30), (30, 20, 10))]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[500, 500],
        loop=0,
        optimize=False,
    )
    output.write_bytes(buffer.getvalue())

    validator = OutputValidator()
    assert await validator.validate_gif(
        output,
        2_400_000,
        ffmpeg=_Probe(),
        expected_fps=2,
        accepted_fps=(2,),
        expected_duration=1.0,
        duration_tolerance=0.05,
    )
    report = await validator.analyze_gif_artifact(output, 2_400_000)
    assert report.duration_ms == 1000
    assert report.effective_fps == pytest.approx(2.0)
    assert report.max_palette_colors <= 256


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_rejects_corrupt_decoded_artifact(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    output.write_bytes(b"GIF89a")
    validator = OutputValidator()
    with pytest.raises(GifAnalysisError):
        await validator.analyze_gif_artifact(output, 2_400_000)


def test_sha256_is_deterministic(tmp_path: Path):
    p = tmp_path / "artifact.gif"
    p.write_bytes(b"GIF89a-test")
    digest = OutputValidator.sha256(p)
    assert len(digest) == 64
    assert digest == OutputValidator.sha256(p)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_rejects_probe_duration_when_decoded_duration_disagrees(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    frames = [Image.new("RGB", (320, 320), (10, 20, 30)), Image.new("RGB", (320, 320), (30, 20, 10))]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[250, 250],
        loop=0,
        optimize=False,
    )
    output.write_bytes(buffer.getvalue())

    class _DishonestProbe:
        async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
            return {
                "format": {"duration": "1.0"},
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 320,
                        "height": 320,
                        "avg_frame_rate": "2/1",
                        "nb_read_frames": "2",
                    }
                ],
            }

    validator = OutputValidator()
    assert not await validator.validate_gif(
        output,
        2_400_000,
        ffmpeg=_DishonestProbe(),
        accepted_fps=(2,),
        expected_fps=2,
        expected_duration=1.0,
        duration_tolerance=0.05,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_rejects_decoded_frame_timing_outside_accepted_fps(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    frames = [Image.new("RGB", (320, 320), color) for color in ((10, 20, 30), (30, 20, 10))]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[400, 400],
        loop=0,
        optimize=False,
    )
    output.write_bytes(buffer.getvalue())

    class _Probe:
        async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
            return {
                "format": {"duration": "0.8"},
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 320,
                        "height": 320,
                        "avg_frame_rate": "2/1",
                        "nb_read_frames": "2",
                    }
                ],
            }

    validator = OutputValidator()
    assert not await validator.validate_gif(
        output,
        2_400_000,
        ffmpeg=_Probe(),
        accepted_fps=(3,),
        expected_fps=3,
        expected_duration=0.8,
        duration_tolerance=0.05,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_cross_checks_decoded_frame_count(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    frames = [Image.new("RGB", (320, 320), color) for color in ((10, 20, 30), (30, 20, 10))]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[500, 500],
        loop=0,
        optimize=False,
    )
    output.write_bytes(buffer.getvalue())

    class _FrameCountMismatchProbe:
        async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
            return {
                "format": {"duration": "1.0"},
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 320,
                        "height": 320,
                        "avg_frame_rate": "2/1",
                        "nb_read_frames": "3",
                    }
                ],
            }

    validator = OutputValidator()
    assert not await validator.validate_gif(
        output,
        2_400_000,
        ffmpeg=_FrameCountMismatchProbe(),
        accepted_fps=(2,),
        expected_fps=2,
        expected_duration=1.0,
        duration_tolerance=0.05,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_rejects_geometry_outside_exact_contract(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    frames = [Image.new("RGB", (320, 320), (10, 20, 30))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", duration=100, loop=0)
    output.write_bytes(buffer.getvalue())

    class _GeometryProbe:
        async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
            return {
                "format": {"duration": "0.1"},
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 321,
                        "height": 320,
                        "avg_frame_rate": "10/1",
                        "nb_read_frames": "1",
                    }
                ],
            }

    assert not await OutputValidator().validate_gif(
        output,
        2_400_000,
        ffmpeg=_GeometryProbe(),
        expected_fps=10,
        accepted_fps=(10,),
        expected_duration=0.1,
        duration_tolerance=0.05,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validator_rejects_fps_outside_closed_accepted_ladder(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    frames = [Image.new("RGB", (320, 320), (10, 20, 30)), Image.new("RGB", (320, 320), (30, 20, 10))]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[330, 330],
        loop=0,
        optimize=False,
    )
    output.write_bytes(buffer.getvalue())

    class _ClosedLadderProbe:
        async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
            return {
                "format": {"duration": "0.66"},
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 320,
                        "height": 320,
                        "avg_frame_rate": "30/1",
                        "nb_read_frames": "2",
                    }
                ],
            }

    assert not await OutputValidator().validate_gif(
        output,
        2_400_000,
        ffmpeg=_ClosedLadderProbe(),
        expected_fps=30,
        accepted_fps=(30, 27, 24, 20, 18, 15),
        expected_duration=0.66,
        duration_tolerance=0.05,
    )


def _gif_header(width: int, height: int, magic: bytes = b"GIF89a") -> bytes:
    return magic + width.to_bytes(2, "little") + height.to_bytes(2, "little") + b"\x00\x00\x00"


@pytest.mark.unit
def test_gif_preflight_rejects_truncated_header() -> None:
    with pytest.raises(GifAnalysisError):
        preflight_gif_budget(b"GIF89a" + b"\x00" * 6, max_width=320, max_height=320)


@pytest.mark.unit
def test_gif_preflight_rejects_wrong_magic() -> None:
    with pytest.raises(GifAnalysisError):
        preflight_gif_budget(_gif_header(320, 320, b"NOTGIF"), max_width=320, max_height=320)


@pytest.mark.unit
def test_gif_preflight_accepts_exact_canvas_boundary() -> None:
    preflight_gif_budget(_gif_header(320, 320), max_width=320, max_height=320)


@pytest.mark.unit
def test_gif_preflight_rejects_width_above_budget() -> None:
    with pytest.raises(GifAnalysisError):
        preflight_gif_budget(_gif_header(321, 320), max_width=320, max_height=320)


@pytest.mark.unit
def test_gif_preflight_rejects_height_above_budget() -> None:
    with pytest.raises(GifAnalysisError):
        preflight_gif_budget(_gif_header(320, 321), max_width=320, max_height=320)


@pytest.mark.unit
def test_gif_preflight_rejects_zero_canvas_dimension() -> None:
    with pytest.raises(GifAnalysisError):
        preflight_gif_budget(_gif_header(0, 320), max_width=320, max_height=320)


@pytest.mark.unit
def test_validator_accepts_exact_output_byte_boundary(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    payload = b"GIF89a" + b"\x40\x01\x40\x01" + b"\x00\x00\x00"
    output.write_bytes(payload + b"x" * (2_400_000 - len(payload)))
    assert OutputValidator().validate_basic_gif(output, 2_400_000)


@pytest.mark.unit
def test_validator_rejects_one_byte_over_output_limit(tmp_path: Path) -> None:
    output = tmp_path / "output.gif"
    payload = b"GIF89a" + b"\x40\x01\x40\x01" + b"\x00\x00\x00"
    output.write_bytes(payload + b"x" * (2_400_001 - len(payload)))
    assert not OutputValidator().validate_basic_gif(output, 2_400_000)
