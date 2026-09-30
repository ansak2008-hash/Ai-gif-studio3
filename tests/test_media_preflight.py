from pathlib import Path

import pytest

from ai_gif_studio.engines.preflight import MediaPreflightError, preflight_media


class FakeFFmpeg:
    def __init__(self, probe):
        self._probe = probe

    async def probe(self, _path: Path, *, count_frames: bool = False):
        assert count_frames is True
        return self._probe


def probe(width=1920, height=1080, frames=120, fps="24/1", duration="5.0"):
    return {
        "streams": [{
            "codec_type": "video",
            "width": width,
            "height": height,
            "nb_read_frames": frames,
            "avg_frame_rate": fps,
        }],
        "format": {"duration": duration},
    }


@pytest.mark.unit
async def test_preflight_returns_verified_media_metadata(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")
    result = await preflight_media(source, FakeFFmpeg(probe()))

    assert result.width == 1920
    assert result.height == 1080
    assert result.frame_count == 120
    assert result.fps == 24
    assert result.duration_seconds == 5


@pytest.mark.unit
async def test_preflight_rejects_missing_video_stream(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")

    with pytest.raises(MediaPreflightError, match="no video stream"):
        await preflight_media(source, FakeFFmpeg({"streams": [], "format": {"duration": "5"}}))


@pytest.mark.unit
async def test_preflight_rejects_oversized_input(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"12345")

    with pytest.raises(MediaPreflightError, match="size limit"):
        await preflight_media(source, FakeFFmpeg(probe()), max_bytes=4)


@pytest.mark.unit
async def test_preflight_rejects_invalid_frame_rate(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")

    with pytest.raises(MediaPreflightError, match="frame rate"):
        await preflight_media(source, FakeFFmpeg(probe(fps="0/1")))


@pytest.mark.unit
async def test_preflight_rejects_dimensions_above_configured_limits(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")

    with pytest.raises(MediaPreflightError, match="width"):
        await preflight_media(source, FakeFFmpeg(probe(width=4000)), max_width=3200)


@pytest.mark.unit
async def test_preflight_rejects_duration_above_configured_limit(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")

    with pytest.raises(MediaPreflightError, match="duration"):
        await preflight_media(source, FakeFFmpeg(probe(duration="61")), max_duration_seconds=60)
