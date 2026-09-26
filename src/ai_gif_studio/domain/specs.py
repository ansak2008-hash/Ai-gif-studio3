from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
DESIGN_SPEC_VERSION=2; PROCESSING_SETTINGS_VERSION=2
class DesignSpec(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True)
    schema_version:int=DESIGN_SPEC_VERSION
    canvas:dict[str,int]=Field(default_factory=lambda:{"width":320,"height":320})
    crop:dict[str,Any]=Field(default_factory=lambda:{"mode":"smart","focus":{"x":0.5,"y":0.5}})
    background:dict[str,Any]=Field(default_factory=lambda:{"mode":"solid","color":"#111111"})
    frame:dict[str,Any]=Field(default_factory=lambda:{"style":"rounded","radius":24})
    motion:dict[str,Any]=Field(default_factory=lambda:{"style":"none"})
    color:dict[str,Any]=Field(default_factory=lambda:{"policy":"adaptive"})
    layers:list[dict[str,Any]]=Field(default_factory=list)
    text:dict[str,Any]|None=None
class ProcessingSettings(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True)
    schema_version:int=PROCESSING_SETTINGS_VERSION
    fps:int=20; max_duration_seconds:float=6.0; max_bytes:int=2_400_000; encoder:str="ffmpeg-gif"; palette_colors:int=256; resource_timeout_seconds:int=120
