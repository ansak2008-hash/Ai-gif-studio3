import subprocess
from pathlib import Path

import pytest

from crop_only_engine import CropOnlyConfiguration, CropOnlyError, crop_video_to_gif
from crop_only_engine.engine import _ffmpeg_command


def test_command_is_real_square_crop_lanczos_palette_pipeline(tmp_path: Path):
    command = _ffmpeg_command("ffmpeg", tmp_path / "source.mp4", tmp_path / "out.gif", 0, 6, 20, CropOnlyConfiguration())
    graph = command[command.index("-filter_complex") + 1]
    assert "crop='min(iw,ih)'" in graph
    assert "scale=320:320:flags=lanczos" in graph
    assert graph.index("scale=320:320") < graph.index("fps=20")
    assert "palettegen=max_colors=256:stats_mode=diff" in graph
    assert "paletteuse=dither=sierra2_4a" in graph
    assert "-hwaccel" in command and command[command.index("-hwaccel") + 1] == "none"


def test_uses_centered_six_second_window_and_falls_down_fps(tmp_path: Path):
    source, target = tmp_path / "in.mp4", tmp_path / "out.gif"
    source.write_bytes(b"source")
    attempts = []

    def runner(command, **_):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, '{"streams":[{"width":1920,"height":1080}],"format":{"duration":"10"}}', "")
        candidate = Path(command[-1]); attempts.append(command)
        candidate.write_bytes(b"x" * (101 if len(attempts) == 1 else 99))
        return subprocess.CompletedProcess(command, 0, "", "")

    result = crop_video_to_gif(source, target, configuration=CropOnlyConfiguration(max_output_bytes=100, fps_ladder=(20, 12)), runner=runner)
    assert (result.start_seconds, result.duration_seconds, result.fps, result.size_bytes) == (2.0, 6.0, 12, 99)
    assert target.stat().st_size == 99
    assert "-ss" in attempts[0] and attempts[0][attempts[0].index("-ss") + 1] == "2.000000"


def test_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="highest to lowest"):
        CropOnlyConfiguration(fps_ladder=(8, 12))


def test_does_not_create_output_when_size_limit_cannot_be_met(tmp_path: Path):
    source, target = tmp_path / "in.mp4", tmp_path / "out.gif"
    source.write_bytes(b"source")

    def runner(command, **_):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, '{"streams":[{"width":1,"height":1}],"format":{"duration":"1"}}', "")
        Path(command[-1]).write_bytes(b"too large")
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(CropOnlyError, match="exceeds"):
        crop_video_to_gif(source, target, configuration=CropOnlyConfiguration(max_output_bytes=1, fps_ladder=(6,)), runner=runner)
    assert not target.exists()
