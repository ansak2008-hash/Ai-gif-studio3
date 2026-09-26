from __future__ import annotations

from typing import Any


def background_filters(spec: dict[str, Any], bounds=None) -> list[str]:
    mode = str(spec.get("mode", "solid"))
    color = str(spec.get("color", "#111111"))
    second = str(spec.get("secondary", "#202020"))
    if bounds is None:
        return []
    x, y, w, h = int(bounds.x), int(bounds.y), int(bounds.width), int(bounds.height)
    right, bottom = x + w, y + h
    if mode == "solid":
        return []
    if mode == "duotone":
        return [f"drawbox=x=0:y=0:w=320:h={max(0,y)}:color={color}:t=fill", f"drawbox=x=0:y={bottom}:w=320:h={max(0,320-bottom)}:color={second}:t=fill"]
    if mode == "stripes":
        return [f"drawbox=x=0:y={band}:w=320:h=40:color={color if i % 2 == 0 else second}:t=fill" for i, band in enumerate(range(0, 320, 40)) if band + 40 <= y or band >= bottom]
    if mode == "luxury":
        return [
            f"drawbox=x=0:y=0:w=320:h={max(0,y)}:color=#08090c:t=fill",
            f"drawbox=x=0:y={bottom}:w=320:h={max(0,320-bottom)}:color=#11131a:t=fill",
            f"drawbox=x=0:y={y}:w={max(0,x)}:h={h}:color=#090a0f:t=fill",
            f"drawbox=x={right}:y={y}:w={max(0,320-right)}:h={h}:color=#090a0f:t=fill",
        ]
    if mode == "sunset":
        return [
            f"drawbox=x=0:y=0:w=320:h={max(0,min(y,106))}:color=#2b124c:t=fill",
            f"drawbox=x=0:y={max(y,106)}:w=320:h={max(0,min(bottom,213)-max(y,106))}:color=#8b3155:t=fill",
            f"drawbox=x=0:y={max(bottom,213)}:w=320:h={max(0,320-max(bottom,213))}:color=#e08a48:t=fill",
        ]
    raise ValueError(f"unsupported background mode: {mode}")


def animated_background_filters(spec: dict[str, Any], bounds, duration: float) -> list[str]:
    filters = background_filters(spec, bounds)
    mode = str(spec.get("animation", "none"))
    if mode == "none" or bounds is None:
        return filters
    x, y, w, h = int(bounds.x), int(bounds.y), int(bounds.width), int(bounds.height)
    if mode == "pulse":
        filters.append(
            f"drawbox=x={x}:y={y}:w={w}:h={h}:color={spec.get('accent', '#ffffff')}@0.12:t='2+3*(0.5+0.5*sin(2*PI*t/2))'
        )
    elif mode == "sweep":
        filters.append(
            f"drawbox=x='({x}-w)+({w}+{x})*mod(t/{max(duration,0.1):.3f},1)':"
            f"y={y}:w={max(2,int(w*0.08))}:h={h}:color={spec.get('accent', '#ffffff')}@0.16:t=fill"
        )
    elif mode == "gradient":
        filters.extend([
            f"drawbox=x={x}:y={y}:w={w}:h={max(1,h//2)}:color={spec.get('color', '#111111')}:t=fill",
            f"drawbox=x={x}:y={y + max(1,h//2)}:w={w}:h={max(1,h-max(1,h//2))}:color={spec.get('secondary', '#202020')}:t=fill"
        ])
    else:
        raise ValueError(f"unsupported background animation: {mode}")
    return filters


def frame_filters(spec: dict[str, Any], animated: bool = False) -> list[str]:
    style, color, second = str(spec.get("style", "rounded")), str(spec.get("color", "#ffffff")), str(spec.get("secondary", "#ffffff"))
    thickness = max(1, min(int(spec.get("thickness", 3)), 16))
    if style in {"none", "transparent"}:
        return []
    if style in {"simple", "rounded", "rounded-rect", "classic"}:
        radius = max(0, min(int(spec.get("radius", 24)), 120))
        if style in {"rounded", "rounded-rect"} and radius > 0:
            # Border geometry is still rectangular here; the true media mask is applied by composition.
            return [f"drawbox=x={thickness}:y={thickness}:w={320-2*thickness}:h={320-2*thickness}:color={color}@0.9:t={thickness}"]
        return [f"drawbox=x={thickness}:y={thickness}:w={320-2*thickness}:h={320-2*thickness}:color={color}@0.9:t={thickness}"]
    if style in {"double", "royal"}:
        return [f"drawbox=x=5:y=5:w=310:h=310:color={color}:t={thickness}", f"drawbox=x=13:y=13:w=294:h=294:color={second}:t={max(1, thickness-1)}"]
    if style == "gold":
        return ["drawbox=x=3:y=3:w=314:h=314:color=#6b4508:t=7", "drawbox=x=9:y=9:w=308:h=308:color=#f6d36b:t=3", "drawbox=x=15:y=15:w=290:h=290:color=#fff0a6@0.75:t=1"]
    if style in {"silver", "chrome"}:
        return ["drawbox=x=3:y=3:w=314:h=314:color=#4d5863:t=7", "drawbox=x=9:y=9:w=308:h=308:color=#dce3e9:t=3", "drawbox=x=15:y=15:w=290:h=290:color=#ffffff@0.8:t=1"]
    if style == "neon":
        if animated:
            return [
                "drawbox=x=4:y=4:w=312:h=312:color=#ff3cf2@0.45:t='6+6*(0.5+0.5*sin(2*PI*t/1.4))'",
                "drawbox=x=8:y=8:w=304:h=304:color=#7df9ff:t=3",
            ]
        return ["drawbox=x=4:y=4:w=312:h=312:color=#ff3cf2@0.45:t=10", "drawbox=x=8:y=8:w=304:h=304:color=#7df9ff:t=3"]
    raise ValueError(f"unsupported frame style: {style}")
