from __future__ import annotations
from pathlib import Path
import hashlib
import numpy as np
from .palette import build_global_palette,quantize_frames_global

def encode_gif(frames:list[np.ndarray],delays_cs:tuple[int,...],output:Path|str)->str:
    if not frames: raise ValueError("frames cannot be empty")
    if len(frames)!=len(delays_cs): raise ValueError("frame/delay count mismatch")
    shape=frames[0].shape
    if shape!=(320,320,3) or any(np.asarray(f).shape!=shape for f in frames): raise ValueError("all frames must be 320x320 RGB")
    if any(int(d)<1 for d in delays_cs): raise ValueError("GIF delays must be >=1cs")
    palette=build_global_palette(frames,256)
    indexed=quantize_frames_global(frames,palette)
    indexed[0].save(str(output),save_all=True,append_images=indexed[1:],duration=[int(d)*10 for d in delays_cs],loop=0,disposal=2,optimize=False)
    return hashlib.sha256(Path(output).read_bytes()).hexdigest()
