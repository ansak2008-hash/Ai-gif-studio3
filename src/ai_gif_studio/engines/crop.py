from __future__ import annotations
from pathlib import Path
from ai_gif_studio.configuration.render import RenderConfiguration
from .quality import QualityEngine
class CropOnlyEngine:
    def __init__(self,ffmpeg,quality=None,render=None): self.ffmpeg=ffmpeg
    self.quality=quality or QualityEngine()
    self.render=render or RenderConfiguration()
    async def convert(self,source:Path,target:Path,settings):
        probe=await self.ffmpeg.probe(source)
        streams=probe.get("streams",[])
        video=next((s for s in streams if s.get("codec_type")=="video"),None)
        if not video:
            raise ValueError("input has no video stream")
        duration=min(float(probe.get("format",{}).get("duration") or settings.max_duration_seconds),settings.max_duration_seconds)
        total=float(probe.get("format",{}).get("duration") or duration)
        start=max(0,(total-duration)/2)
        ladder=[]
        for fps in (settings.fps,16,12,10,8,6):
            if fps not in ladder:
                ladder.append(fps)
        for fps in ladder:
            palette=target.with_suffix(".palette.png")
            vf=f"fps={fps},crop='min(iw,ih)':'min(iw,ih)',scale={self.render.canvas_width}:{self.render.canvas_height}:flags=lanczos"
            await self.ffmpeg.run(["-ss",f"{start:.3f}","-t",f"{duration:.3f}","-i",str(source),"-vf",vf+f",palettegen=max_colors={self.render.palette_colors}:stats_mode=diff",str(palette)])
            await self.ffmpeg.run(["-ss",f"{start:.3f}","-t",f"{duration:.3f}","-i",str(source),"-i",str(palette),"-lavfi",f"{vf}[x];[x][1:v]paletteuse=dither=sierra2_4a","-an","-loop","0",str(target)])
            palette.unlink(missing_ok=True)
            if target.exists() and target.stat().st_size<=settings.max_bytes:
                return target
        target.unlink(missing_ok=True)
        raise ValueError("output exceeds configured size limit after fallback ladder")
