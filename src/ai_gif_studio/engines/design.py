from __future__ import annotations
from pathlib import Path
from ai_gif_studio.domain.specs import DesignSpec,ProcessingSettings
class DesignGifEngine:
    def __init__(self,ffmpeg): self.ffmpeg=ffmpeg
    async def convert(self,source:Path,target:Path,design:DesignSpec,settings:ProcessingSettings):
        probe=await self.ffmpeg.probe(source); total=float(probe.get("format",{}).get("duration") or settings.max_duration_seconds)
        duration=min(total,settings.max_duration_seconds); start=max(0,(total-duration)/2)
        bg=design.background.get("color","#111111"); size=280
        for fps in (settings.fps,16,12,10,8,6):
            if fps<=0: continue
            vf=f"fps={fps},crop='min(iw,ih)':'min(iw,ih)',scale={size}:{size}:flags=lanczos,pad=320:320:(ow-iw)/2:(oh-ih)/2:color={bg}"
            if design.frame.get("style")!="none":
                vf += ",drawbox=x=0:y=0:w=320:h=320:color=#ffffff@0.75:t=3"
            palette=target.with_suffix(".palette.png")
            await self.ffmpeg.run(["-ss",f"{start:.3f}","-t",f"{duration:.3f}","-i",str(source),"-vf",vf+",palettegen=max_colors=256:stats_mode=diff",str(palette)])
            await self.ffmpeg.run(["-ss",f"{start:.3f}","-t",f"{duration:.3f}","-i",str(source),"-i",str(palette),"-lavfi",f"{vf}[x];[x][1:v]paletteuse=dither=sierra2_4a","-an","-loop","0",str(target)])
            palette.unlink(missing_ok=True)
            if target.exists() and target.stat().st_size<=settings.max_bytes:return target
        target.unlink(missing_ok=True); raise ValueError("designed GIF exceeds size limit after fallback ladder")
