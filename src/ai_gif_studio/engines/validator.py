from __future__ import annotations
from pathlib import Path
import imghdr, subprocess
class OutputValidator:
    def validate_gif(self,path:Path,max_bytes:int,width:int=320,height:int=320):
        if not path.exists() or path.stat().st_size>max_bytes: return False
        if path.read_bytes()[:6] not in (b"GIF87a",b"GIF89a"): return False
        p=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",str(path)],capture_output=True,text=True,timeout=20)
        return p.returncode==0 and p.stdout.strip()==f"{width},{height}"
