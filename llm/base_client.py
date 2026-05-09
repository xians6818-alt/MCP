from abc import ABC, abstractmethod
from typing import Any, Dict

from models.copywriting import OptimizedScriptResult, ScriptIdeaResult
from models.rubric import Rubric
from models.score import DimensionScores


class BaseLLMClient(ABC):
    @abstractmethod
    def score_script(self, script: str, rubric: Rubric) -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_script_ideas(self, product_info: str) -> ScriptIdeaResult:
        pass

    @abstractmethod
    def optimize_script(self, original_script: str, score_context: Dict[str, Any]) -> OptimizedScriptResult:
        pass

    @abstractmethod
    def analyze_counterfactual(self, script: str, scores: DimensionScores, composite: float, bucket: str) -> str:
        pass

    @abstractmethod
    def audit_bump(self, old_rubric: Rubric, new_rubric: Rubric, calibration_data: list) -> Dict[str, Any]:
        pass
