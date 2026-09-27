from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class WorkflowStep: name:str
capability:str|None=None
optional:bool=False
@dataclass(frozen=True, slots=True)
class Workflow: id:str
steps:tuple[WorkflowStep,...]
CROP_ONLY_WORKFLOW=Workflow("crop_only",(WorkflowStep("probe"),WorkflowStep("crop","crop"),WorkflowStep("quality"),WorkflowStep("encode"),WorkflowStep("validate"),WorkflowStep("deliver")))
DESIGN_GIF_WORKFLOW=Workflow("design_gif",(WorkflowStep("probe"),WorkflowStep("crop","crop"),WorkflowStep("compose","compose"),WorkflowStep("quality"),WorkflowStep("encode"),WorkflowStep("validate"),WorkflowStep("deliver")))