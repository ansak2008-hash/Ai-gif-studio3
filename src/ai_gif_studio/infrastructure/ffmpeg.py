from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path

from ai_gif_studio.domain.probe_errors import (
    ProbeCorruptMediaError,
    ProbeExecutionError,
    ProbeTimeoutError,
)


class FFmpegError(RuntimeError):
    pass


class FFmpegTimeoutError(FFmpegError):
    pass


class FFmpegCommandError(FFmpegError):
    pass


class FFmpegService:
    def __init__(self, ffmpeg="ffmpeg", ffprobe="ffprobe", timeout=120):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.timeout = timeout

    async def _run(self, args: Sequence[str], timeout=None):
        env = {
            **os.environ,
            "FFREPORT": "file=/dev/null",
            "http_proxy": "",
            "https_proxy": "",
        }
        p = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            out, err = await asyncio.wait_for(p.communicate(), timeout or self.timeout)
        except TimeoutError:
            p.kill()
            await p.wait()
            raise FFmpegTimeoutError("ffmpeg timeout") from None
        if p.returncode:
            raise FFmpegCommandError((err or out).decode(errors="replace")[-4000:])
        return out, err

    async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
        args = [self.ffprobe, "-v", "error"]
        if count_frames:
            args.append("-count_frames")
        args += ["-show_streams", "-show_format", "-of", "json", str(path)]
        try:
            out, _ = await self._run(args)
        except FFmpegTimeoutError as exc:
            raise ProbeTimeoutError(f"probe timed out: {path}") from exc
        except FFmpegCommandError as exc:
            raise ProbeExecutionError(str(exc)) from exc
        try:
            return json.loads(out)
        except json.JSONDecodeError as exc:
            raise ProbeCorruptMediaError(f"invalid ffprobe output: {path}") from exc

    async def run(self, args: Sequence[str]):
        return await self._run([self.ffmpeg, "-hide_banner", "-nostdin", "-y", *args])
