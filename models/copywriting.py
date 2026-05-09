from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ScriptIdea(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    style: str = ""
    title: str = ""
    script: str = ""
    hook: str = ""
    selling_points: List[str] = Field(default_factory=list)


class ScriptIdeaResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    ideas: List[ScriptIdea] = Field(default_factory=list)


class OptimizedScriptResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str = ""
    optimized_script: str
    key_changes: List[str] = Field(default_factory=list)
    target_improvements: List[str] = Field(default_factory=list)
