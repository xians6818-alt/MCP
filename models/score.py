from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clamp_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(5, score))


class DimensionScores(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    ER: int = Field(default=0, ge=0, le=5)
    SR: int = Field(default=0, ge=0, le=5)
    HP: int = Field(default=0, ge=0, le=5)
    QL: int = Field(default=0, ge=0, le=5)
    NA: int = Field(default=0, ge=0, le=5)
    AB: int = Field(default=0, ge=0, le=5)
    SAT: int = Field(default=0, ge=0, le=5)

    @field_validator("ER", "SR", "HP", "QL", "NA", "AB", "SAT", mode="before")
    @classmethod
    def normalize_score(cls, value: Any) -> int:
        return _clamp_score(value)

    def to_dict(self) -> Dict[str, int]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DimensionScores":
        return cls.model_validate(data or {})

    @classmethod
    def from_llm_dict(cls, data: Dict[str, Any]) -> "DimensionScores":
        required = {"ER", "SR", "HP", "QL", "NA", "AB", "SAT"}
        normalized = {str(key).strip().upper(): value for key, value in (data or {}).items()}
        missing = sorted(required - set(normalized))
        if missing:
            available = ", ".join(sorted(normalized.keys())) or "无"
            raise ValueError(f"LLM评分结果缺少必要字段：{', '.join(missing)}。已收到字段：{available}")
        return cls.model_validate({key: normalized[key] for key in required})


class StoryboardScene(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    scene: str = ""
    duration_seconds: int = Field(default=0, ge=0, le=600)
    location: str = ""
    shot_type: str = ""
    camera_movement: str = ""
    description: str = ""
    subject_action: str = ""
    narration: str = ""
    subtitle: str = ""
    audio: str = ""
    props: str = ""
    execution_notes: str = ""

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def normalize_duration(cls, value: Any) -> int:
        try:
            duration = int(round(float(value)))
        except (TypeError, ValueError):
            return 0
        return max(0, min(600, duration))

    def get(self, key: str, default: str = "") -> str:
        return getattr(self, key, default)


class ShootingGuide(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    lighting: str = ""
    sound: str = ""
    performance: str = ""
    schedule: str = ""
    location_plan: str = ""
    equipment: str = ""
    props: str = ""
    crew: str = ""
    cover_title: str = ""
    platform_notes: str = ""
    risk_notes: str = ""


class ScoreResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    scores: DimensionScores
    composite: float = Field(ge=0, le=10)
    reasons: Dict[str, str] = Field(default_factory=dict)
    storyboard_guide: List[StoryboardScene] = Field(default_factory=list)
    shooting_guide: Optional[ShootingGuide] = None

    @field_validator("composite", mode="before")
    @classmethod
    def normalize_composite(cls, value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(10.0, score))

    def __str__(self):
        return f"ScoreResult(composite={self.composite:.2f}, scores={self.scores.to_dict()})"
