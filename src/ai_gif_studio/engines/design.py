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

        crop_w = max(1, int(round(crop.width)))
        crop_h = max(1, int(round(crop.height)))
        crop_x = max(0, int(round(crop.x)))
        crop_y = max(0, int(round(crop.y)))
        media_w = max(1, int(round(bounds.width)))
        media_h = max(1, int(round(bounds.height)))
        media_x = int(round(bounds.x))
        media_y = int(round(bounds.y))

        frame_style = str(design.frame.get("style", "rounded-rect"))
        frame_color = str(design.frame.get("color", "#ffffff"))
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
