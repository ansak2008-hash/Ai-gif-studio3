from __future__ import annotations

from pathlib import Path

from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.composition import square_layout
from ai_gif_studio.engines.styles import background_filters, frame_filters
from ai_gif_studio.engines.typography import TypographyRenderer
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
        crop_w, crop_h = max(1, int(crop["width"])), max(1, int(crop["height"]))
        base_x, base_y = max(0, int(crop["x"])), max(0, int(crop["y"]))
        amount = max(0.0, min(float(design.motion.get("amount", 8)), 24.0))
        style = str(design.motion.get("style", "none"))
        if style == "float":
            crop_x = f"{base_x}+{amount:.2f}*sin(2*PI*t/{duration:.3f})"
            crop_y = f"{base_y}+{amount:.2f}*cos(2*PI*t/{duration:.3f})"
        elif style == "pan":
            crop_x, crop_y = f"{base_x}+(iw-{crop_w}-{base_x})*t/{duration:.3f}", str(base_y)
        else:
            crop_x, crop_y = str(base_x), str(base_y)
        bg = design.background
        bg_color = str(bg.get("color", "#111111"))
        filters = [
            f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}",
            f"scale={max(1, int(bounds.width))}:{max(1, int(bounds.height))}:flags=lanczos",
            f"pad=320:320:{int(bounds.x)}:{int(bounds.y)}:color={bg_color}",
        ]
        filters.extend(background_filters(bg, bounds))
        filters.extend(frame_filters(design.frame))
        for layer in design.layers:
            filters.append(
                f"drawbox=x=0:y=0:w=320:h=320:color={layer.get('color', '#ffffff')}@"
                f"{float(layer.get('opacity', 1.0))}:t={int(layer.get('thickness', 3))}"
            )
        if design.text is not None and design.text.get("enabled", True):
            text = str(design.text.get("content", "")).replace("\\", "\\\\").replace(":", "\\:")
            filters.append(
                f"drawtext=text='{text}':fontsize={int(design.text.get('size', 24))}:"
                f"fontcolor={design.text.get('color', '#ffffff')}:x={int(design.text.get('x', 16))}:"
                f"y={int(design.text.get('y', 280))}:box=1:boxcolor=black@0.35:boxborderw=6:text_shaping=1"
            )
        overlay_file = target.parent / "typography.txt"
        if design.typography is not None:
            filters.extend(await TypographyRenderer().filters(design.typography, target.parent))
        vf = ",".join(filters)
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
            overlay_file.unlink(missing_ok=True)
