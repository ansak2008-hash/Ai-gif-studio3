from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path


class FFmpegError(RuntimeError):
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
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "all_proxy": "",
            "ALL_PROXY": "",
            "no_proxy": "*",
            "NO_PROXY": "*",
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
            raise FFmpegError("ffmpeg timeout") from None
        if p.returncode:
            raise FFmpegError((err or out).decode(errors="replace")[-4000:])
        return out, err

    async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
        args = [
            self.ffprobe,
            "-v",
            "error",
            "-max_streams",
            "32",
            "-max_pixels",
            "33177600",
        ]
        if count_frames:
            args.append("-count_frames")
        args += ["-show_streams", "-show_format", "-of", "json", str(path)]
        out, _ = await self._run(args)
        return json.loads(out)

    async def run(self, args: Sequence[str]):
        return await self._run([self.ffmpeg, "-hide_banner", "-nostdin", "-y", *args])
