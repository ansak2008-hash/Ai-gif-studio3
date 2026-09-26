from __future__ import annotations

from pathlib import Path

from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.composition import square_layout


class DesignGifEngine:
    """Deterministic DesignSpec -> GIF renderer.

    AI capabilities are intentionally not invoked here; unsupported DesignSpec
    features remain explicit instead of being silently approximated.
    """

    def __init__(self, ffmpeg, render: RenderConfiguration | None = None):
        self.ffmpeg = ffmpeg
        self.render = render or RenderConfiguration()

    async def convert(
        self,
        source: Path,
        target: Path,
        design: DesignSpec,
        settings: ProcessingSettings,
    ):
        probe = await self.ffmpeg.probe(source)
        video = next(
            (item for item in probe.get("streams", []) if item.get("codec_type") == "video"),
            None,
        )
        if video is None:
            raise ValueError("input has no video stream")

        source_width = int(video.get("width") or 0)
        source_height = int(video.get("height") or 0)
        if source_width <= 0 or source_height <= 0:
            raise ValueError("input video dimensions are invalid")

        total = float(probe.get("format", {}).get("duration") or settings.max_duration_seconds)
        duration = min(total, settings.max_duration_seconds, self.render.duration_seconds)
        start = max(0.0, (total - duration) / 2.0)

        focus = design.crop.get("focus", {})
        layout = square_layout(
            source_width,
            source_height,
            float(focus.get("x", 0.5)),
            float(focus.get("y", 0.5)),
            density=0.52,
            shape=design.frame.get("style", "rounded-rect"),
            anchor=design.crop.get("anchor", "center"),
        )
        crop = layout["crop"]
        bounds = layout["foreground_bounds"]
        bg = str(design.background.get("color", "#111111"))
        if not bg.startswith("#") or len(bg) not in (4, 7):
            raise ValueError("background color must be a hex color")

        crop_w = max(1, int(round(crop["width"])))
        crop_h = max(1, int(round(crop["height"])))
        crop_x = max(0, int(round(crop["x"])))
        crop_y = max(0, int(round(crop["y"])))
        media_w = max(1, int(round(bounds.width)))
        media_h = max(1, int(round(bounds.height)))
        media_x = int(round(bounds.x))
        media_y = int(round(bounds.y))

        frame_style = str(design.frame.get("style", "rounded-rect"))
        frame_color = str(design.frame.get("color", "#ffffff"))
        motion = design.motion
        motion_style = str(motion.get("style", "none"))
        motion_amount = max(0.0, min(float(motion.get("amount", 0.0)), 0.12))
        if motion_style not in {"none", "float", "pan"}:
            raise ValueError("unsupported motion style")
        layers = design.layers
        if len(layers) > 8:
            raise ValueError("too many design layers")
        for layer in layers:
            if str(layer.get("type", "")) not in {"shape", "border", "accent"}:
                raise ValueError("unsupported design layer type")
        text = design.text
        if text is not None:
            if not isinstance(text, dict) or len(str(text.get("content", ""))) > 160:
                raise ValueError("text content is invalid")
            if text.get("enabled", True) and not str(text.get("content", "")):
                raise ValueError("enabled text requires content")
        if motion_style not in {"none", "float", "pan"}:
            raise ValueError("unsupported motion style")
        filters = [
            f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}",
            f"scale={media_w}:{media_h}:flags=lanczos",
            f"pad={self.render.canvas_width}:{self.render.canvas_height}:{media_x}:{media_y}:color={bg}",
        ]
        if frame_style not in {"none", "transparent"}:
            filters.append(
                f"drawbox=x=0:y=0:w={self.render.canvas_width}:h={self.render.canvas_height}:"
                f"color={frame_color}@0.75:t=3"
            )
        for layer in layers:
            if str(layer.get("type")) in {"border", "accent"}:
                thickness = max(1, min(int(layer.get("thickness", 3)), 20))
                color = str(layer.get("color", "#ffffff"))
                opacity = max(0.0, min(float(layer.get("opacity", 1.0)), 1.0))
                filters.append(
                    f"drawbox=x=0:y=0:w={self.render.canvas_width}:h={self.render.canvas_height}:"
                    f"color={color}@{opacity}:t={thickness}"
                )
        if text is not None and text.get("enabled", True):
            content_text = str(text.get("content", "")).replace(":", "\\:")
            font_size = max(10, min(int(text.get("size", 24)), 72))
            x = int(text.get("x", 16))
            y = int(text.get("y", 280))
            color = str(text.get("color", "#ffffff"))
            filters.append(
                f"drawtext=text='{content_text}':fontsize={font_size}:fontcolor={color}:"
                f"x={x}:y={y}:box=1:boxcolor=black@0.35:boxborderw=6"
            )
        vf_base = ",".join(filters)

        ladder = tuple(
            dict.fromkeys(
                fps
                for fps in (settings.fps, *self.render.fps_fallback_ladder)
                if fps > 0
            )
        )
        palette = target.with_suffix(".palette.png")
        try:
            for fps in ladder:
                await self.ffmpeg.run(
                    [
                        "-ss", f"{start:.3f}",
                        "-t", f"{duration:.3f}",
                        "-i", str(source),
                        "-vf",
                        f"fps={fps},{vf_base},"
                        f"palettegen=max_colors={min(settings.palette_colors, self.render.palette_colors)}:stats_mode=diff",
                        str(palette),
                    ]
                )
                await self.ffmpeg.run(
                    [
                        "-ss", f"{start:.3f}",
                        "-t", f"{duration:.3f}",
                        "-i", str(source),
                        "-i", str(palette),
                        "-lavfi",
                        f"{vf_base},fps={fps}[x];"
                        f"[x][1:v]paletteuse=dither=sierra2_4a",
                        "-an",
                        "-loop", "0",
                        str(target),
                    ]
                )
                if target.is_file() and target.stat().st_size <= min(
                    settings.max_bytes, self.render.maximum_output_bytes
                ):
                    return target
            target.unlink(missing_ok=True)
            raise ValueError("designed GIF exceeds size limit after fallback ladder")
        finally:
            palette.unlink(missing_ok=True)
