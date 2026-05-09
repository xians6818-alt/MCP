from typing import Any, Dict, List

from llm.base_client import BaseLLMClient
from models.copywriting import OptimizedScriptResult, ScriptIdeaResult
from models.score import ScoreResult


class Copywriter:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def generate_ideas(self, product_info: str) -> ScriptIdeaResult:
        if not product_info.strip():
            raise ValueError("Product or brand information is required.")
        return self.llm_client.generate_script_ideas(product_info)

    def optimize(self, original_script: str, score_result: ScoreResult) -> OptimizedScriptResult:
        if not original_script.strip():
            raise ValueError("Original script is required.")

        score_context = {
            "composite": round(score_result.composite, 2),
            "scores": score_result.scores.to_dict(),
            "reasons": score_result.reasons,
            "weaknesses": self._weaknesses(score_result),
        }
        return self.llm_client.optimize_script(original_script, score_context)

    def _weaknesses(self, score_result: ScoreResult) -> List[Dict[str, Any]]:
        weaknesses = []
        for key, value in score_result.scores.to_dict().items():
            if value <= 3:
                weaknesses.append(
                    {
                        "dimension": key,
                        "score": value,
                        "reason": score_result.reasons.get(key, ""),
                    }
                )
        weaknesses.sort(key=lambda item: item["score"])
        return weaknesses
