from typing import Any, Dict, List, Optional

from llm.base_client import BaseLLMClient
from models.rubric import Rubric, RubricVersion
from models.score import DimensionScores


class ValidationResult:
    def __init__(self):
        self.consistency: float = 0.0
        self.pairwise_regression: bool = False
        self.audit_passed: bool = False
        self.audit_reason: str = ""
        self.audit_risks: List[str] = []
        self.passed: bool = False

    def __str__(self):
        return f"ValidationResult(passed={self.passed}, consistency={self.consistency:.2f}, audit_passed={self.audit_passed})"


class BumpValidator:
    THRESHOLD = 0.8

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def _rescore_all(self, new_rubric: Rubric, calibration_pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rescores = []
        for sample in calibration_pool:
            scores = DimensionScores.from_dict(sample)
            weights = new_rubric.current_weights
            total = sum(scores.to_dict().get(dim, 0) * weights.get(dim, 1.0) for dim in scores.to_dict())
            new_composite = total / new_rubric.normalization_constant * 2.0

            rescores.append(
                {
                    "title": sample.get("title", ""),
                    "old_composite": sample.get("composite", 0),
                    "new_composite": new_composite,
                    "actual_plays": sample.get("actual_plays", 0),
                    "scores": scores.to_dict(),
                }
            )

        return rescores

    def _calculate_consistency(self, rescores: List[Dict[str, Any]]) -> float:
        if len(rescores) < 2:
            return 1.0

        new_ranks = sorted(range(len(rescores)), key=lambda i: rescores[i]["new_composite"], reverse=True)
        actual_ranks = sorted(range(len(rescores)), key=lambda i: rescores[i]["actual_plays"], reverse=True)

        correct = 0
        for index in range(len(rescores)):
            if new_ranks[index] == actual_ranks[index]:
                correct += 1

        return correct / len(rescores)

    def _check_pairwise_regression(self, rescores: List[Dict[str, Any]]) -> bool:
        for i in range(len(rescores)):
            for j in range(len(rescores)):
                if i == j:
                    continue

                old_i_better = rescores[i]["old_composite"] > rescores[j]["old_composite"]
                actual_i_better = rescores[i]["actual_plays"] > rescores[j]["actual_plays"]
                new_i_better = rescores[i]["new_composite"] > rescores[j]["new_composite"]

                if old_i_better == actual_i_better and new_i_better != actual_i_better:
                    return True

        return False

    def validate(self, old_rubric: Rubric, new_rubric: Rubric, calibration_pool: List[Dict[str, Any]]) -> ValidationResult:
        result = ValidationResult()

        if not calibration_pool:
            result.audit_reason = "校准池为空，无法验证rubric升级。"
            return result

        rescores = self._rescore_all(new_rubric, calibration_pool)
        result.consistency = self._calculate_consistency(rescores)
        result.pairwise_regression = self._check_pairwise_regression(rescores)

        if result.consistency < self.THRESHOLD or result.pairwise_regression:
            result.audit_reason = "排序一致性不足或存在pairwise回归。"
            return result

        audit_result = self.llm_client.audit_bump(old_rubric, new_rubric, rescores)
        result.audit_passed = audit_result.get("判定") == "PASS" or audit_result.get("鍒ゅ畾") == "PASS"
        result.audit_reason = audit_result.get("理由") or audit_result.get("鐞嗙敱", "")
        result.audit_risks = audit_result.get("关键风险") or audit_result.get("鍏抽敭椋庨櫓", [])
        result.passed = result.consistency >= self.THRESHOLD and not result.pairwise_regression and result.audit_passed

        return result

    def propose_bump(self, current_rubric: Rubric, proposal: str) -> Optional[Rubric]:
        try:
            new_weights = current_rubric.current_weights.copy()

            for raw_part in proposal.split(","):
                part = raw_part.strip()
                if not part:
                    continue

                if any(symbol in part for symbol in ["*", "x", "×"]):
                    symbol = "*" if "*" in part else "x" if "x" in part else "×"
                    dim, weight = part.split(symbol, 1)
                    dim = dim.strip().upper()
                    if dim in new_weights:
                        new_weights[dim] = float(weight.strip())
                    continue

                if part.startswith(("add ", "新增", "加")):
                    dim_name = part.replace("add ", "").replace("新增", "").replace("加", "").strip().upper()
                    if dim_name:
                        new_weights[dim_name] = 1.0
                    continue

                if part.startswith(("delete ", "remove ", "删除", "删")):
                    dim_name = (
                        part.replace("delete ", "")
                        .replace("remove ", "")
                        .replace("删除", "")
                        .replace("删", "")
                        .strip()
                        .upper()
                    )
                    new_weights.pop(dim_name, None)

            norm_const = sum(new_weights.values())
            if norm_const <= 0:
                return None

            version_num = int(current_rubric.current_version[1:]) + 1
            new_version = f"v{version_num}"
            formula_parts = [dim if weight == 1.0 else f"{dim}*{weight}" for dim, weight in new_weights.items()]

            return Rubric(
                versions=current_rubric.versions
                + [
                    RubricVersion(
                        version=new_version,
                        formula=f"composite = ({' + '.join(formula_parts)}) / {norm_const} * 2.0",
                        weights=new_weights,
                        normalization_constant=norm_const,
                        description=f"升级自{current_rubric.current_version}",
                    )
                ],
                dimensions=current_rubric.dimensions,
                current_version=new_version,
            )
        except Exception:
            return None
