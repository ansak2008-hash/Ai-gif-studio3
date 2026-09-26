from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Bounds: x:float; y:float; width:float; height:float
def _clamp(v,a,b): return max(a,min(b,v))
def _round(v): return round(v,2)
def _design_ratio(source_ratio:float,shape:str)->float:
    if shape=="circle": return 1.0
    if source_ratio>=1.35: return 1.08
    if source_ratio<=0.74: return 0.82
    return _clamp(source_ratio,.88,1.12)
def square_layout(width:int,height:int,focus_x:float=.5,focus_y:float=.5,density:float=.52,shape:str="rounded-rect",anchor:str="center"):
    if width<=0 or height<=0: raise ValueError("source dimensions must be positive")
    focus_x=_clamp(focus_x,0,1); focus_y=_clamp(focus_y,0,1); density=_clamp(density,0,1)
    source_ratio=width/height; ratio=_design_ratio(source_ratio,shape); scale=_clamp(.70+density*.25,.70,.95); long=320*scale
    fw=long if ratio>=1 else long*ratio; fh=long/ratio if ratio>=1 else long; x=(320-fw)/2; natural=(320-fh)/2; nudge=(320-fh)*.16
    y=natural-nudge if anchor=="top" else natural+nudge if anchor=="bottom" else natural
    if width >= height:
        ch=height; cw=ch
    else:
        cw=width; ch=cw
    cx=_clamp(focus_x*width-cw/2,0,width-cw); cy=_clamp(focus_y*height-ch/2,0,height-ch)
    return {"canvas":{"width":320,"height":320},"source_aspect":source_ratio,"foreground_bounds":Bounds(_round(x),_round(y),_round(fw),_round(fh)),"media_bounds":Bounds(_round(x),_round(y),_round(fw),_round(fh)),"crop":{"x":_round(cx),"y":_round(cy),"width":_round(cw),"height":_round(ch)},"shape":shape,"radius":_round(min(fw,fh)/2 if shape=="circle" else min(fw,fh)*.1 if shape=="rounded-rect" else 0),"breathing_room":{"top":_round(y),"right":_round(320-x-fw),"bottom":_round(320-y-fh),"left":_round(x)}}


def media_mask_filter(bounds: Bounds, shape: str, radius: float = 24.0) -> str:
    """Return a real alpha mask for the foreground media, preserving the canvas background."""
    w, h = max(1, int(bounds.width)), max(1, int(bounds.height))
    shape = str(shape)
    if shape == "circle":
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0
        expr = f"if(lte((X-{cx:.2f})*(X-{cx:.2f})+(Y-{cy:.2f})*(Y-{cy:.2f}),{r:.2f}*{r:.2f}),255,0)"
    elif shape in {"rounded", "rounded-rect"}:
        r = max(0.0, min(float(radius), min(w, h) / 2.0))
        # Rounded-rectangle distance field: central rectangle + quarter-circle corners.
        cx, cy = w / 2.0, h / 2.0
        expr = (
            f"if(lte(pow(max(abs(X-{cx:.2f})-({w/2-r:.2f}),0),2)+"
            f"pow(max(abs(Y-{cy:.2f})-({h/2-r:.2f}),0),2),{r:.2f}*{r:.2f}),255,0)"
        )
    else:
        expr = "255"
    return f"format=rgba,geq=a='{expr}'"
