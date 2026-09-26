from __future__ import annotations

from pathlib import Path

FONT_CANDIDATES = {
    "arabic": ("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf", "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    "arabic_bold": ("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf", "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    "latin": ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    "latin_bold": ("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
}
MATERIALS = {
    "flat": {"fill": "#ffffff", "shadow": "#000000@0.45", "highlight": "#ffffff"},
    "gold": {"fill": "#f6d36b", "shadow": "#6b4b08@0.85", "highlight": "#fff4b0"},
    "silver": {"fill": "#e8edf2", "shadow": "#46515d@0.85", "highlight": "#ffffff"},
    "chrome": {"fill": "#d8e0e8", "shadow": "#20262c@0.9", "highlight": "#ffffff"},
    "neon": {"fill": "#7df9ff", "shadow": "#ff3cf2@0.8", "highlight": "#ffffff"},
}
STYLES = {"flat", "bold", "calligraphy", "3d", "extruded", "gold", "silver", "chrome", "neon"}

def resolve_font(script: str, weight: str = "regular") -> str:
    key = "arabic" if script == "arabic" else "latin"
    if weight in {"bold", "black"}:
        key += "_bold"
    for path in FONT_CANDIDATES[key]:
        if Path(path).is_file():
            return path
    raise RuntimeError(f"no supported {key} font is installed")

def _animation_expressions(animation: str, x: int, y: int) -> tuple[str, str, str]:
    if animation == "fade":
        return str(x), str(y), ":alpha='1-exp(-8*t)'"
    if animation == "slide":
        return f"{x-80}+80*(1-exp(-6*t))", str(y), ""
    if animation == "pulse":
        return str(x), str(y), ":alpha='0.72+0.28*(0.5+0.5*sin(2*PI*t/1.5))'"
    if animation == "shine":
        return str(x), str(y), ":alpha='0.72+0.28*(0.5+0.5*sin(2*PI*t/1.2))'"
    return str(x), str(y), ""


def _drawtext(font: str, textfile: Path, size: int, color: str, x: str, y: str, options: str = "") -> str:
    return (
        f"drawtext=fontfile={font}:textfile={textfile}:text_shaping=1:"
        f"fontsize={size}:fontcolor={color}:x={x}:y={y}{options}"
    )

def render_text_filters(spec: dict, textfile: Path) -> list[str]:
    content = str(spec.get("content", ""))
    if not content:
        return []
    script = str(spec.get("script", "arabic" if any("\u0600" <= c <= "\u06ff" for c in content) else "latin"))
    style = str(spec.get("style", "bold"))
    material = str(spec.get("material", "flat"))
    animation = str(spec.get("animation", "none"))
    size = max(10, min(int(spec.get("size", 48)), 120))
    x, y = int(spec.get("x", 24)), int(spec.get("y", 240))
    font = resolve_font(script, "bold" if style in {"bold", "3d", "extruded", "gold", "silver", "chrome", "neon"} else "regular")
    palette = MATERIALS.get(material, MATERIALS["flat"])
    ax, ay, animation_options = _animation_expressions(animation, x, y)
    filters = []
    if style in {"3d", "extruded", "gold", "silver", "chrome"}:
        depth = max(2, min(int(spec.get("depth", 6)), 16))
        for offset in range(depth, 0, -1):
            filters.append(_drawtext(font, textfile, size, palette["shadow"], f"({ax})+{offset}", f"({ay})+{offset}", animation_options))
    filters.append(_drawtext(font, textfile, size, palette["fill"], ax, ay, animation_options))
    if material in {"gold", "silver", "chrome", "neon"}:
        filters.append(_drawtext(font, textfile, max(10, size-2), palette["highlight"], ax, f"({ay})-1", animation_options))
    return filters

class TypographyRenderer:
    async def filters(self, spec: dict, directory: Path) -> list[str]:
        text = str(spec.get("content", ""))
        if len(text) > 160:
            raise ValueError("typography content must be at most 160 characters")
        if not text:
            return []
        textfile = directory / "overlay.txt"
        textfile.write_text(text, encoding="utf-8")
        return render_text_filters(spec, textfile)
