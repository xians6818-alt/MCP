from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .score import ScoreResult


def _clamp_probability(value: Any) -> float:
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, probability))


class BucketDistribution(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    bucket: str
    probability: float = Field(ge=0, le=1)

    @field_validator("probability", mode="before")
    @classmethod
    def normalize_probability(cls, value: Any) -> float:
        return _clamp_probability(value)


class AnchorItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str
    composite: float = 0.0
    actual_plays: float = 0.0
    similarities: str = ""
    differences: str = ""


class CounterfactualScenario(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    bucket_range: str
    probability: float = Field(ge=0, le=1)
    verified_hypotheses: List[str] = Field(default_factory=list)
    rejected_hypotheses: List[str] = Field(default_factory=list)
    new_dimensions: List[str] = Field(default_factory=list)
    explanation: str = ""

    @field_validator("probability", mode="before")
    @classmethod
    def normalize_probability(cls, value: Any) -> float:
        return _clamp_probability(value)


class CalibrationHypothesis(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    comparison_target: str
    expected_ratio: str
    if_reversed: str
    if_close: str


class Prediction(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    article_id: str
    title: str
    script_path: str
    script_hash: str
    rubric_version: str
    prediction_time: datetime
    score_result: ScoreResult
    bucket: str
    center: float
    distribution: List[BucketDistribution]
    anchors: List[AnchorItem] = Field(default_factory=list)
    counterfactuals: List[CounterfactualScenario] = Field(default_factory=list)
    calibration_hypothesis: Optional[CalibrationHypothesis] = None
    confidence: str = "低"
    scored_by: str = "system"
    user_override: str = "none"

    def _storyboard_markdown(self) -> str:
        if not self.score_result.storyboard_guide:
            return "暂无可执行分镜。"

        lines = [
            "| 镜号 | 秒 | 地点 | 景别 | 运镜 | 画面 | 动作 | 旁白/同期声 | 字幕 | 声音 | 道具 | 执行注意 |",
            "|---|---:|---|---|---|---|---|---|---|---|---|---|",
        ]
        for scene in self.score_result.storyboard_guide:
            lines.append(
                "| "
                + " | ".join(
                    [
                        scene.scene,
                        str(scene.duration_seconds),
                        scene.location,
                        scene.shot_type,
                        scene.camera_movement,
                        scene.description,
                        scene.subject_action,
                        scene.narration,
                        scene.subtitle,
                        scene.audio,
                        scene.props,
                        scene.execution_notes,
                    ]
                )
                + " |"
            )
        return "\n".join(lines)

    def _shooting_guide_markdown(self) -> str:
        guide = self.score_result.shooting_guide
        if not guide:
            return "暂无拍摄执行指导。"

        rows = [
            ("光线与色彩", guide.lighting),
            ("声音与BGM", guide.sound),
            ("出镜与表演", guide.performance),
            ("拍摄顺序", guide.schedule),
            ("取景点规划", guide.location_plan),
            ("设备清单", guide.equipment),
            ("道具清单", guide.props),
            ("人员分工", guide.crew),
            ("封面标题", guide.cover_title),
            ("平台适配", guide.platform_notes),
            ("风险提醒", guide.risk_notes),
        ]
        lines = ["| 项目 | 建议 |", "|---|---|"]
        for label, value in rows:
            lines.append(f"| {label} | {value or '暂无建议'} |")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        scores = self.score_result.scores
        dist_lines = "\n".join(
            [f"- `{item.bucket}` -> {int(item.probability * 100)}%" for item in self.distribution]
        )

        anchor_lines = []
        if self.anchors:
            anchor_lines.append("| 对照样本 | composite | 真实播放量 | 相似点 | 差异点 |")
            anchor_lines.append("|---|---:|---:|---|---|")
            for anchor in self.anchors:
                anchor_lines.append(
                    f"| {anchor.title} | {anchor.composite:.2f} | {anchor.actual_plays}w | "
                    f"{anchor.similarities} | {anchor.differences} |"
                )
        else:
            anchor_lines.append("校准池样本不足，暂无锚点对比。")

        counterfactual_lines = []
        for item in self.counterfactuals:
            counterfactual_lines.append(
                f"**如果落在 `{item.bucket_range}`**（{int(item.probability * 100)}% 预期）"
            )
            if item.verified_hypotheses:
                counterfactual_lines.append(f"- 验证：{', '.join(item.verified_hypotheses)}")
            if item.rejected_hypotheses:
                counterfactual_lines.append(f"- 推翻：{', '.join(item.rejected_hypotheses)}")
            if item.new_dimensions:
                counterfactual_lines.append(f"- 新增观察维度：{', '.join(item.new_dimensions)}")
            if item.explanation:
                counterfactual_lines.append(f"- 解释：{item.explanation}")
            counterfactual_lines.append("")

        hypothesis_section = ""
        if self.calibration_hypothesis:
            hypothesis = self.calibration_hypothesis
            hypothesis_section = f"""## 关键校准假设

对比目标：{hypothesis.comparison_target}
预期比例：{hypothesis.expected_ratio}

- 如果结果反转：{hypothesis.if_reversed}
- 如果差距小于预期：{hypothesis.if_close}
"""

        return f"""# {self.title} - 预测日志

**Article ID**: {self.article_id}
**Title**: {self.title}
**Rubric Version**: **{self.rubric_version}**
**预测时间**: {self.prediction_time.strftime("%Y-%m-%d %H:%M:%S")}
**Script Path**: {self.script_path}
**Script Hash**: {self.script_hash}
**Confidence**: {self.confidence}
**Scored By**: {self.scored_by}
**User Override**: {self.user_override}
**预测时数据状态**: blind

## 输入快照

**分数 ({self.rubric_version})**: ER{scores.ER} / SR{scores.SR} / HP{scores.HP} / QL{scores.QL} / NA{scores.NA} / AB{scores.AB} / SAT{scores.SAT} -> composite=**{self.score_result.composite:.2f}**

## 预测

**Bucket**: `{self.bucket}`
**中枢播放量**: {self.center:.1f}w

**概率分布**:
{dist_lines}

## 可执行分镜脚本

{self._storyboard_markdown()}

## 拍摄执行指导

{self._shooting_guide_markdown()}

## 锚点对比

{chr(10).join(anchor_lines)}

## 反事实场景

{chr(10).join(counterfactual_lines) if counterfactual_lines else "暂无反事实分析。"}

{hypothesis_section}

## 复盘

待填：发布后 T+3 天补充真实播放量、互动数据和异常说明。
"""
