from datetime import datetime
import hashlib
from typing import List

from core.analyzer import Analyzer
from core.rubric_engine import RubricEngine
from models.prediction import (
    AnchorItem,
    BucketDistribution,
    CalibrationHypothesis,
    CounterfactualScenario,
    Prediction,
)
from models.score import ScoreResult


class Predictor:
    def __init__(self, rubric_engine: RubricEngine, analyzer: Analyzer):
        self.engine = rubric_engine
        self.analyzer = analyzer
        self.calibration_pool = []

    def load_calibration_pool(self, pool: List[dict]):
        self.calibration_pool = pool or []

    def _distribution(self, rows: List[tuple]) -> List[BucketDistribution]:
        return [BucketDistribution(bucket=bucket, probability=probability) for bucket, probability in rows]

    def _calculate_bucket(self, composite: float) -> tuple:
        if composite >= 8.0:
            primary_bucket = "30-100w" if composite < 9.0 else "100-150w"
            center = 65.0 if composite < 9.0 else 125.0
            distribution = self._distribution(
                [
                    ("<5w", 0.02),
                    ("5-30w", 0.15),
                    ("30-100w", 0.50 if composite < 9.0 else 0.30),
                    ("100-150w", 0.28),
                    (">150w", 0.05),
                ]
            )
        elif composite >= 6.0:
            primary_bucket = "5-30w"
            center = 17.5
            distribution = self._distribution(
                [
                    ("<5w", 0.08),
                    ("5-30w", 0.55),
                    ("30-100w", 0.30),
                    ("100-150w", 0.05),
                    (">150w", 0.02),
                ]
            )
        else:
            primary_bucket = "<5w" if composite < 4.0 else "5-30w"
            center = 2.5 if composite < 4.0 else 17.5
            distribution = self._distribution(
                [
                    ("<5w", 0.30 if composite < 4.0 else 0.15),
                    ("5-30w", 0.40 if composite < 4.0 else 0.50),
                    ("30-100w", 0.20 if composite < 4.0 else 0.28),
                    ("100-150w", 0.08 if composite < 4.0 else 0.05),
                    (">150w", 0.02),
                ]
            )

        return primary_bucket, distribution, center

    def _create_anchors(self, score_result: ScoreResult) -> List[AnchorItem]:
        anchors = []
        for data in self.analyzer.find_anchors(score_result.composite, self.calibration_pool):
            anchors.append(
                AnchorItem(
                    title=data.get("title", "Unknown"),
                    composite=data.get("composite", 0),
                    actual_plays=data.get("actual_plays", 0),
                    similarities=data.get("similarities", ""),
                    differences=data.get("differences", ""),
                )
            )
        return anchors

    def _create_counterfactuals(
        self, script: str, score_result: ScoreResult, bucket: str
    ) -> List[CounterfactualScenario]:
        return self.analyzer.analyze_counterfactual(
            script,
            score_result.scores,
            score_result.composite,
            bucket,
        )

    def predict(self, script: str, title: str, script_path: str) -> Prediction:
        score_result = self.engine.score(script)
        bucket, distribution, center = self._calculate_bucket(score_result.composite)
        anchors = self._create_anchors(score_result)
        counterfactuals = self._create_counterfactuals(script, score_result, bucket)

        article_id = hashlib.sha256(script.encode("utf-8")).hexdigest()[:12]
        script_hash = self.engine.calculate_script_hash(script)
        confidence = self._get_confidence(len(self.calibration_pool))

        hypothesis = None
        if self.calibration_pool:
            hypothesis = CalibrationHypothesis(
                comparison_target="上一条同类内容",
                expected_ratio="1.5-2x",
                if_reversed="需要复查评分维度权重，尤其是开头钩子、转化意图和平台适配。",
                if_close="rubric方向基本可用，差异可能来自封面、发布时间、账号状态或投流噪声。",
            )

        return Prediction(
            article_id=article_id,
            title=title,
            script_path=script_path,
            script_hash=script_hash,
            rubric_version=self.engine.rubric.current_version,
            prediction_time=datetime.now(),
            score_result=score_result,
            bucket=bucket,
            center=center,
            distribution=distribution,
            anchors=anchors,
            counterfactuals=counterfactuals,
            calibration_hypothesis=hypothesis,
            confidence=confidence,
            scored_by="system",
            user_override="none",
        )

    def _get_confidence(self, sample_count: int) -> str:
        if sample_count >= 20:
            return "高（中枢可信，约±20%）"
        if sample_count >= 10:
            return "中（中枢可信，约±30%）"
        if sample_count >= 5:
            return "偏低（中枢约±40%）"
        if sample_count >= 3:
            return "低（中枢约±50%）"
        return "极低（冷启动，仅供参考）"
