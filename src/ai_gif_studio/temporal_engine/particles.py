from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class ParticleField:
    count:int=90
    seed:int=20260927
    max_radius:float=3.0
    def __post_init__(self):
        if self.count<0 or self.max_radius<0: raise ValueError("invalid particle field")
    def points(self,width,height):
        rng=np.random.default_rng(self.seed)
        xy=rng.random((self.count,2),dtype=np.float32)*np.array([width,height],np.float32)
        depth=rng.random(self.count,dtype=np.float32)
        radius=(0.5+depth*self.max_radius).astype(np.float32)
        phase=rng.random(self.count,dtype=np.float32)*np.float32(2*np.pi)
        return xy,depth,radius,phase

def render_particles(shape,field,time,camera_scale=1.0):
    h,w=shape; out=np.zeros((h,w,3),np.float32)
    xy,depth,radius,phase=field.points(w,h); yy,xx=np.ogrid[:h,:w]
    for (x,y),d,r,p in zip(xy,depth,radius,phase):
        parallax=(0.15+0.85*d)*max(camera_scale-1,0)
        px=x+(x-w/2)*parallax*.10+np.cos(p+time*.7)*(1+d*2)
        py=y+(y-h/2)*parallax*.06+np.sin(p+time*.55)*(1+d*1.5)
        sigma=max(.5,float(r)*(.6+.8*d))
        blob=np.exp(-((xx-px)**2+(yy-py)**2)/(2*sigma*sigma)).astype(np.float32)
        out+=blob[...,None]*(.04+.16*d)*(.7+.3*np.sin(p+time*1.2))
    return out
