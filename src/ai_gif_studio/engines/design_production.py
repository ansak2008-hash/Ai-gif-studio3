from __future__ import annotations

from pathlib import Path

from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.composition import square_layout
from ai_gif_studio.motion_engine import pad_expression
from ai_gif_studio.quality_engine import QualityEngine


class ProductionDesignGifEngine:
    def __init__(self, ffmpeg, render=None, quality=None):
        self.ffmpeg = ffmpeg
        self.render = render or RenderConfiguration()
        self.quality = quality or QualityEngine()

    async def convert(self, source: Path, target: Path, design: DesignSpec, settings: ProcessingSettings):
        probe = await self.ffmpeg.probe(source)
        video = next((x for x in probe.get("streams", []) if x.get("codec_type") == "video"), None)
        if video is None:
            raise ValueError("input has no video stream")
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        total = float(probe.get("format", {}).get("duration") or settings.max_duration_seconds)
        duration = min(total, settings.max_duration_seconds, self.render.duration_seconds)
        start = max(0.0, (total - duration) / 2.0)
        focus = design.crop.get("focus", {})
        layout = square_layout(width, height, float(focus.get("x", 0.5)), float(focus.get("y", 0.5)), density=0.52, shape=design.frame.get("style", "rounded"), anchor="center")
        crop = layout["crop"]
        bounds = layout["foreground_bounds"]
        x, y = pad_expression(str(design.motion.get("style", "none")), float(design.motion.get("amount", 8)), duration)
        if design.motion.get("style", "none") == "none":
            x, y = str(int(round(bounds.x))), str(int(round(bounds.y)))
        vf = ",".join([
            f"crop={max(1, int(crop['width']))}:{max(1, int(crop['height']))}:{max(0, int(crop['x']))}:{max(0, int(crop['y']))}",
            f"scale={max(1, int(bounds.width))}:{max(1, int(bounds.height))}:flags=lanczos",
            f"pad=320:320:x='{x}':y='{y}':color={design.background.get('color', '#111111')}:eval=frame",
        ])
        palette = target.with_suffix(".palette.png")
        try:
            for fps in self.quality.ladder(settings.fps):
                await self.ffmpeg.run(["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source), "-vf", f"fps={fps},{vf},palettegen=max_colors={settings.palette_colors}:stats_mode=diff", str(palette)])
                await self.ffmpeg.run(["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source), "-i", str(palette), "-lavfi", f"{vf},fps={fps}[x];[x][1:v]paletteuse=dither=sierra2_4a", "-an", "-loop", "0", str(target)])
                if (await self.quality.inspect(target, self.ffmpeg, settings.max_bytes, selected_fps=fps)).valid:
                    return target
            raise ValueError("designed GIF exceeds quality limits")
        finally:
            palette.unlink(missing_ok=True)
