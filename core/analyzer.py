from typing import Any, Dict, List

from llm.base_client import BaseLLMClient
from models.prediction import CounterfactualScenario
from models.score import DimensionScores


class Analyzer:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def analyze_counterfactual(
        self, script: str, scores: DimensionScores, composite: float, bucket: str
    ) -> List[CounterfactualScenario]:
        llm_response = self.llm_client.analyze_counterfactual(script, scores, composite, bucket)
        return self._parse_counterfactual_response(llm_response)

    def _parse_counterfactual_response(self, response: str) -> List[CounterfactualScenario]:
        scenarios = []
        current_scenario = None

        scenario_defs = [
            ("1.", "如果爆", "高播放", 0.15),
            ("2.", "如果落在预期", "预期区间", 0.60),
            ("3.", "如果表现低于预期", "低于预期", 0.20),
            ("4.", "如果表现极差", "极差", 0.05),
        ]

        for raw_line in (response or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue

            matched = False
            for prefix, title, bucket_range, probability in scenario_defs:
                if line.startswith(prefix) or title in line:
                    if current_scenario:
                        scenarios.append(current_scenario)
                    current_scenario = CounterfactualScenario(bucket_range=bucket_range, probability=probability)
                    matched = True
                    break
            if matched or not current_scenario:
                continue

            content = line.lstrip("-").strip()
            if content.startswith("验证"):
                current_scenario.verified_hypotheses.append(self._clean_label(content))
            elif content.startswith("推翻"):
                current_scenario.rejected_hypotheses.append(self._clean_label(content))
            elif content.startswith("可能新增") or content.startswith("新增"):
                current_scenario.new_dimensions.append(self._clean_label(content))
            elif content.startswith("基准线") or content.startswith("极端场景") or content.startswith("解释"):
                current_scenario.explanation = self._clean_label(content)
            else:
                if current_scenario.explanation:
                    current_scenario.explanation += f" {content}"
                else:
                    current_scenario.explanation = content

        if current_scenario:
            scenarios.append(current_scenario)

        if not scenarios and response:
            scenarios.append(
                CounterfactualScenario(
                    bucket_range="未结构化分析",
                    probability=1.0,
                    explanation=response.strip(),
                )
            )

        return scenarios

    def _clean_label(self, text: str) -> str:
        for separator in ["：", ":"]:
            if separator in text:
                return text.split(separator, 1)[1].strip()
        return text.strip()

    def find_anchors(self, composite: float, calibration_pool: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
        anchors = []
        for sample in calibration_pool:
            sample_composite = sample.get("composite", 0)
            if abs(sample_composite - composite) <= 0.5:
                anchors.append(sample)

        anchors.sort(key=lambda item: abs(item.get("composite", 0) - composite))
        return anchors[:limit]
