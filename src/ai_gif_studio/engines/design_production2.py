from __future__ import annotations

from pathlib import Path

from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.composition import Bounds, media_mask_filter, square_layout
from ai_gif_studio.engines.filtergraph import build_filtergraph
from ai_gif_studio.engines.styles import animated_background_filters, frame_filters
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
        shape = str(design.frame.get("shape", design.crop.get("shape", layout.get("shape", "rounded"))))
        if shape not in {"rect", "rounded", "rounded-rect", "circle"}:
            shape = "rounded"
        mask = media_mask_filter(
            Bounds(0, 0, bounds.width, bounds.height),
            shape,
            float(design.frame.get("radius", layout.get("radius", 24))),
        )
        typography_filters = []
        if design.typography is not None:
            typography_filters = await TypographyRenderer().filters(design.typography, target.parent)
        overlay_x, overlay_y = int(bounds.x), int(bounds.y)
        base_filters = [
            f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={max(1, int(bounds.width))}:{max(1, int(bounds.height))}:flags=lanczos,{mask}[fg]",
            f"color=c={bg_color}:s=320x320:r=30:d={duration:.3f}[bg]",
        ]
        background_chain = animated_background_filters(bg, bounds, duration)
        base_filters.append(
            f"[bg]{','.join(background_chain)}[bgstyled]"
            if background_chain
            else "[bg]null[bgstyled]"
        )
        composition_filters = [
            f"[bgstyled][fg]overlay=x={overlay_x}:y={overlay_y}:shortest=1[composed]",
        ]
        composition_filters.extend(
            f"[composed]{','.join(frame_filters(design.frame, animated=True))}[framed]"
            if frame_filters(design.frame, animated=True)
            else "[composed]null[framed]"
        )
        current = "framed"
        if design.layers:
            for idx, layer in enumerate(design.layers):
                opacity = float(layer.get("opacity", 1.0))
                thickness = int(layer.get("thickness", 3))
                color = str(layer.get("color", "#ffffff"))
                layer_type = str(layer.get("type", "accent"))
                if layer_type == "border":
                    layer_filter = f"drawbox=x={thickness}:y={thickness}:w={320-2*thickness}:h={320-2*thickness}:color={color}@{opacity}:t={thickness}"
                elif layer_type == "accent":
                    layer_filter = f"drawbox=x=0:y=0:w=320:h=320:color={color}@{opacity}:t={thickness}"
                else:
                    layer_filter = f"drawbox=x={int(layer.get('x', 0))}:y={int(layer.get('y', 0))}:w={max(1,int(layer.get('width', 32)))}:h={max(1,int(layer.get('height', 32)))}:color={color}@{opacity}:t=fill"
                nxt = f"layer{idx}"
                composition_filters.append(f"[{current}]{layer_filter}[{nxt}]")
                current = nxt
        if design.text is not None and design.text.get("enabled", True):
            text = str(design.text.get("content", "")).replace("\\", "\\\\").replace(":", "\\:")
            text_filter = (
                f"drawtext=text='{text}':fontsize={int(design.text.get('size', 24))}:"
                f"fontcolor={design.text.get('color', '#ffffff')}:x={int(design.text.get('x', 16))}:"
                f"y={int(design.text.get('y', 280))}:box=1:boxcolor=black@0.35:boxborderw=6:text_shaping=1"
            )
            composition_filters.append(f"[{current}]{text_filter}[texted]")
            current = "texted"
        if typography_filters:
            composition_filters.append(f"[{current}]{','.join(typography_filters)}[out]")
        else:
            composition_filters.append(f"[{current}]null[out]")
        vf = build_filtergraph(base_filters + composition_filters)
        palette = target.with_suffix(".palette.png")
        try:
            for fps in self.quality.ladder(settings.fps):
                await self.ffmpeg.run(["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source), "-filter_complex", f"{vf};[out]fps={fps},palettegen=max_colors={settings.palette_colors}:stats_mode=diff[pal]", "-map", "[pal]", str(palette)])
                await self.ffmpeg.run(["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source), "-i", str(palette), "-filter_complex", f"{vf};[out]fps={fps}[x];[x][1:v]paletteuse=dither=sierra2_4a[outgif]", "-map", "[outgif]", "-an", "-loop", "0", str(target)])
                if (await self.quality.inspect(target, self.ffmpeg, settings.max_bytes, selected_fps=fps)).valid:
                    return target
            raise ValueError("designed GIF exceeds quality limits")
        finally:
            palette.unlink(missing_ok=True)
