from __future__ import annotations

def background_filters(spec: dict) -> list[str]:
    mode, color, second = str(spec.get("mode", "solid")), str(spec.get("color", "#111111")), str(spec.get("secondary", "#202020"))
    if mode == "solid":
        return [f"drawbox=x=0:y=0:w=320:h=320:color={color}:t=fill"]
    if mode == "duotone":
        return [f"drawbox=x=0:y=0:w=320:h=160:color={color}:t=fill", f"drawbox=x=0:y=160:w=320:h=160:color={second}:t=fill"]
    if mode == "stripes":
        return [f"drawbox=x=0:y={y}:w=320:h=80:color={color if y % 160 == 0 else second}:t=fill" for y in (0,80,160,240)]
    if mode == "luxury":
        return ["drawbox=x=0:y=0:w=320:h=320:color=#08090c:t=fill", "drawbox=x=12:y=12:w=296:h=296:color=#11131a:t=fill", "drawbox=x=18:y=18:w=284:h=284:color=#090a0f:t=fill"]
    if mode == "sunset":
        return ["drawbox=x=0:y=0:w=320:h=106:color=#2b124c:t=fill", "drawbox=x=0:y=106:w=320:h=107:color=#8b3155:t=fill", "drawbox=x=0:y=213:w=320:h=107:color=#e08a48:t=fill"]
    raise ValueError(f"unsupported background mode: {mode}")

def frame_filters(spec: dict) -> list[str]:
    style, color, second = str(spec.get("style", "rounded")), str(spec.get("color", "#ffffff")), str(spec.get("secondary", "#ffffff"))
    thickness = max(1, min(int(spec.get("thickness", 3)), 16))
    if style in {"none", "transparent"}: return []
    if style in {"simple", "rounded", "classic"}: return [f"drawbox=x={thickness}:y={thickness}:w={320-2*thickness}:h={320-2*thickness}:color={color}@0.9:t={thickness}"]
    if style in {"double", "royal"}: return [f"drawbox=x=5:y=5:w=310:h=310:color={color}:t={thickness}", f"drawbox=x=13:y=13:w=294:h=294:color={second}:t={max(1, thickness-1)}"]
    if style == "gold": return ["drawbox=x=3:y=3:w=314:h=314:color=#6b4508:t=7", "drawbox=x=9:y=9:w=308:h=308:color=#f6d36b:t=3", "drawbox=x=15:y=15:w=290:h=290:color=#fff0a6@0.75:t=1"]
    if style in {"silver", "chrome"}: return ["drawbox=x=3:y=3:w=314:h=314:color=#4d5863:t=7", "drawbox=x=9:y=9:w=308:h=308:color=#dce3e9:t=3", "drawbox=x=15:y=15:w=290:h=290:color=#ffffff@0.8:t=1"]
    if style == "neon": return ["drawbox=x=4:y=4:w=312:h=312:color=#ff3cf2@0.45:t=10", "drawbox=x=8:y=8:w=304:h=304:color=#7df9ff:t=3"]
    raise ValueError(f"unsupported frame style: {style}")
