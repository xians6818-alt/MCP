from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Dimension(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str
    key: str
    weight: float = Field(default=1.0, gt=0)
    description: str
    examples_0: str
    examples_3: str
    examples_5: str

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip().upper()


class RubricVersion(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    version: str
    formula: str
    weights: Dict[str, float] = Field(default_factory=dict)
    normalization_constant: float = Field(gt=0)
    description: str = ""

    @field_validator("weights")
    @classmethod
    def normalize_weights(cls, value: Dict[str, float]) -> Dict[str, float]:
        normalized = {}
        for key, weight in (value or {}).items():
            normalized[key.strip().upper()] = max(float(weight), 0.0)
        return normalized


class Rubric(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    versions: List[RubricVersion] = Field(default_factory=list)
    dimensions: List[Dimension] = Field(default_factory=list)
    current_version: str = "v0"

    @property
    def current_weights(self) -> Dict[str, float]:
        for version in self.versions:
            if version.version == self.current_version:
                return version.weights
        return {}

    @property
    def normalization_constant(self) -> float:
        for version in self.versions:
            if version.version == self.current_version:
                return version.normalization_constant
        return 7.0

    def get_dimension(self, key: str) -> Dimension:
        normalized_key = key.strip().upper()
        for dim in self.dimensions:
            if dim.key == normalized_key:
                return dim
        raise ValueError(f"Dimension {normalized_key} not found")

    def format_rules(self) -> str:
        rules = []
        weights = self.current_weights
        for dim in self.dimensions:
            weight = weights.get(dim.key, dim.weight)
            rules.append(
                f"""### {dim.key} - {dim.name}（权重 x{weight}）
{dim.description}

- 0分：{dim.examples_0}
- 3分：{dim.examples_3}
- 5分：{dim.examples_5}
"""
            )
        return "\n".join(rules)
