from pathlib import Path

import pytest

from ai_gif_studio.domain.probe_errors import ProbeExecutionError
from ai_gif_studio.engines.validator import OutputValidator
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
    import shutil
    import subprocess

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
    assert await validator.validate_gif(out, 2_400_000, expected_fps=8, expected_duration=1.0, duration_tolerance=0.35)



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

def test_sha256_is_deterministic(tmp_path: Path):
    p = tmp_path / "artifact.gif"
    p.write_bytes(b"GIF89a-test")
    digest = OutputValidator.sha256(p)
    assert len(digest) == 64
    assert digest == OutputValidator.sha256(p)
