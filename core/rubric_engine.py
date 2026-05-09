import hashlib
from typing import Any, Dict, List, Optional

from llm.base_client import BaseLLMClient
from models.rubric import Dimension, Rubric, RubricVersion
from models.score import DimensionScores, ScoreResult, ShootingGuide, StoryboardScene


class RubricEngine:
    REQUIRED_SCORE_KEYS = ("ER", "SR", "HP", "QL", "NA", "AB", "SAT")

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client
        self.rubric = self._load_default_rubric()

    def _load_default_rubric(self) -> Rubric:
        dimensions = [
            Dimension(
                name="Emotional Resonance",
                key="ER",
                weight=1.5,
                description="Whether the first 30 seconds create a specific and nameable emotion.",
                examples_0="Pure information delivery with no emotional hook.",
                examples_3="General resonance, such as making viewers feel they have had a similar feeling.",
                examples_5="Sharp and concrete emotion that triggers strong self-recognition.",
            ),
            Dimension(
                name="Social Resonance",
                key="SR",
                weight=1.5,
                description="Whether the script touches a current social pattern, tension, or shared belief.",
                examples_0="Only a personal anecdote or plain introduction.",
                examples_3="Touches a common social phenomenon but without a fresh angle.",
                examples_5="Names a social emotion or structure that viewers know but rarely articulate.",
            ),
            Dimension(
                name="Hook Potential",
                key="HP",
                weight=1.5,
                description="Whether the first 3 seconds force viewers to keep watching.",
                examples_0="Generic opening such as a plain greeting or simple introduction.",
                examples_3="Contains a concrete promise, contrast, or light suspense.",
                examples_5="Starts with a vivid image, conflict, counterintuitive claim, or strong benefit.",
            ),
            Dimension(
                name="Quotable Lines",
                key="QL",
                weight=1.0,
                description="Whether the script has lines that can be screenshotted, repeated, or shared alone.",
                examples_0="Plain narration with no memorable line.",
                examples_3="One line is relatively memorable.",
                examples_5="Multiple independently shareable lines placed at key moments.",
            ),
            Dimension(
                name="Narrativity",
                key="NA",
                weight=1.0,
                description="Whether the script has a clear setup, escalation, and payoff instead of a list of selling points.",
                examples_0="List-style introduction with no narrative movement.",
                examples_3="Loose main thread with average turn and ending.",
                examples_5="Tight structure with a hook, mid-section escalation, and a clear payoff.",
            ),
            Dimension(
                name="Audience Breadth",
                key="AB",
                weight=1.0,
                description="Whether the topic has broad potential audience appeal.",
                examples_0="Very niche; only useful for one interest group or professional group.",
                examples_3="Medium breadth; covers a clear user group.",
                examples_5="Broad topic covering family, work, emotion, parent-child, healing, or travel needs.",
            ),
            Dimension(
                name="Satire Depth",
                key="SAT",
                weight=1.0,
                description="Whether contrast, irony, self-mockery, or layered expression increases shareability.",
                examples_0="Sincere direct statement with no contrast.",
                examples_3="One layer of contrast or light irony.",
                examples_5="Layered irony, self-reference, or strong contrast that can trigger comments.",
            ),
        ]

        versions = [
            RubricVersion(
                version="v0",
                formula="composite = (ER + SR + HP + QL + NA + AB + SAT) / 7 * 2.0",
                weights={"ER": 1.0, "SR": 1.0, "HP": 1.0, "QL": 1.0, "NA": 1.0, "AB": 1.0, "SAT": 1.0},
                normalization_constant=7.0,
                description="Equal-weight cold-start version.",
            ),
            RubricVersion(
                version="v2",
                formula="composite = (ER*1.5 + SR*1.5 + HP*1.5 + QL + NA + AB + SAT) / 8.5 * 2.0",
                weights={"ER": 1.5, "SR": 1.5, "HP": 1.5, "QL": 1.0, "NA": 1.0, "AB": 1.0, "SAT": 1.0},
                normalization_constant=8.5,
                description="Current calibrated version with higher weight on emotion, social resonance, and hook.",
            ),
        ]

        return Rubric(versions=versions, dimensions=dimensions, current_version="v2")

    def calculate_composite(self, scores: DimensionScores) -> float:
        weights = self.rubric.current_weights
        total = (
            scores.ER * weights.get("ER", 1.0)
            + scores.SR * weights.get("SR", 1.0)
            + scores.HP * weights.get("HP", 1.0)
            + scores.QL * weights.get("QL", 1.0)
            + scores.NA * weights.get("NA", 1.0)
            + scores.AB * weights.get("AB", 1.0)
            + scores.SAT * weights.get("SAT", 1.0)
        )
        return total / self.rubric.normalization_constant * 2.0

    def _normalize_llm_result(self, raw_result: Any) -> Dict[str, Any]:
        if not isinstance(raw_result, dict):
            raise ValueError(f"LLM score result must be a JSON object, got {type(raw_result).__name__}.")

        result = dict(raw_result)
        nested_scores = result.get("scores") or result.get("score") or result.get("评分")
        if isinstance(nested_scores, dict):
            for key, value in nested_scores.items():
                result.setdefault(str(key).strip().upper(), value)

        for key in list(result.keys()):
            upper_key = str(key).strip().upper()
            if upper_key in self.REQUIRED_SCORE_KEYS and upper_key != key:
                result[upper_key] = result[key]

        if "storyboard_guide" not in result:
            for alias in ("storyboard", "storyboards", "shots", "shot_list", "分镜", "分镜脚本"):
                if alias in result:
                    result["storyboard_guide"] = result[alias]
                    break

        if "shooting_guide" not in result:
            for alias in ("shooting", "shooting_plan", "production_guide", "拍摄指导", "拍摄方案"):
                if alias in result:
                    result["shooting_guide"] = result[alias]
                    break

        if "reasons" not in result:
            for alias in ("reason", "score_reasons", "评分理由"):
                if alias in result:
                    result["reasons"] = result[alias]
                    break

        self._validate_llm_result(result)
        return result

    def _validate_llm_result(self, result: Dict[str, Any]):
        missing_scores = [key for key in self.REQUIRED_SCORE_KEYS if key not in result]
        if missing_scores:
            raise ValueError(
                "LLM score result is missing required score fields: "
                + ", ".join(missing_scores)
                + f". Received fields: {', '.join(map(str, result.keys()))}"
            )

        reasons = result.get("reasons")
        if not isinstance(reasons, dict) or not reasons:
            raise ValueError("LLM score result is missing a non-empty 'reasons' object.")

        storyboard = result.get("storyboard_guide")
        if not isinstance(storyboard, list) or not storyboard:
            raise ValueError("LLM score result is missing a non-empty 'storyboard_guide' array.")

        shooting_guide = result.get("shooting_guide")
        if not isinstance(shooting_guide, dict) or not shooting_guide:
            raise ValueError("LLM score result is missing a non-empty 'shooting_guide' object.")

    def _normalize_storyboard_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        aliases = {
            "scene": ("scene", "镜号", "镜头", "shot", "shot_id"),
            "duration_seconds": ("duration_seconds", "duration", "seconds", "时长", "秒数"),
            "location": ("location", "地点", "场景", "取景点"),
            "shot_type": ("shot_type", "景别", "镜别"),
            "camera_movement": ("camera_movement", "运镜", "镜头运动"),
            "description": ("description", "画面", "画面描述", "内容"),
            "subject_action": ("subject_action", "人物动作", "主体动作", "动作"),
            "narration": ("narration", "旁白", "同期声", "台词"),
            "subtitle": ("subtitle", "字幕", "屏幕字幕"),
            "audio": ("audio", "声音", "BGM", "环境声"),
            "props": ("props", "道具"),
            "execution_notes": ("execution_notes", "执行注意", "注意事项", "备注"),
        }
        normalized = {}
        for target, keys in aliases.items():
            for key in keys:
                if key in item:
                    normalized[target] = item[key]
                    break
        return normalized

    def _parse_storyboard_guide(self, raw_guide: Any) -> List[StoryboardScene]:
        if not isinstance(raw_guide, list):
            raise ValueError("storyboard_guide must be an array.")

        parsed = []
        for item in raw_guide:
            if isinstance(item, StoryboardScene):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(StoryboardScene.model_validate(self._normalize_storyboard_item(item)))
            else:
                raise ValueError(f"Each storyboard item must be an object, got {type(item).__name__}.")
        if not parsed:
            raise ValueError("storyboard_guide is empty.")
        return parsed

    def _parse_shooting_guide(self, raw_guide: Any) -> Optional[ShootingGuide]:
        if isinstance(raw_guide, ShootingGuide):
            return raw_guide
        if isinstance(raw_guide, dict):
            aliases = {
                "lighting": ("lighting", "光线", "光线与色彩"),
                "sound": ("sound", "声音", "BGM", "环境声"),
                "performance": ("performance", "表演", "出镜", "出镜与表演"),
                "schedule": ("schedule", "拍摄顺序", "时间安排"),
                "location_plan": ("location_plan", "取景点规划", "场景规划"),
                "equipment": ("equipment", "设备", "设备清单"),
                "props": ("props", "道具", "道具清单"),
                "crew": ("crew", "人员", "人员分工"),
                "cover_title": ("cover_title", "封面标题", "标题"),
                "platform_notes": ("platform_notes", "平台适配", "平台建议"),
                "risk_notes": ("risk_notes", "风险", "风险提醒"),
            }
            normalized = {}
            for target, keys in aliases.items():
                for key in keys:
                    if key in raw_guide:
                        normalized[target] = raw_guide[key]
                        break
            return ShootingGuide.model_validate(normalized or raw_guide)
        raise ValueError("shooting_guide must be an object.")

    def _parse_reasons(self, raw_reasons: Any) -> Dict[str, str]:
        if not isinstance(raw_reasons, dict):
            raise ValueError("reasons must be an object.")
        return {str(key).upper(): str(value) for key, value in raw_reasons.items()}

    def score(self, script: str) -> ScoreResult:
        raw_result = self.llm_client.score_script(script, self.rubric)
        raw_result = self._normalize_llm_result(raw_result)
        scores = DimensionScores.from_llm_dict(raw_result)
        composite = self.calculate_composite(scores)

        return ScoreResult(
            scores=scores,
            composite=composite,
            reasons=self._parse_reasons(raw_result.get("reasons", {})),
            storyboard_guide=self._parse_storyboard_guide(raw_result.get("storyboard_guide", [])),
            shooting_guide=self._parse_shooting_guide(raw_result.get("shooting_guide", {})),
        )

    def calculate_script_hash(self, script: str) -> str:
        return hashlib.sha256(script.encode("utf-8")).hexdigest()[:12]
