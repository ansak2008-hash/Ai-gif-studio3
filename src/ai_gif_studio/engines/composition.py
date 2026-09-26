from __future__ import annotations
def square_layout(width:int,height:int,focus_x:float=.5,focus_y:float=.5)->dict:
    side=min(width,height); x=max(0,min(width-side,focus_x*width-side/2)); y=max(0,min(height-side,focus_y*height-side/2))
    return {"canvas":{"width":320,"height":320},"crop":{"x":round(x),"y":round(y),"width":side,"height":side},"shape":"rounded-rect","radius":24}
