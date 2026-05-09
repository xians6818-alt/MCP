import json
import re
from typing import Any, Dict, List

from openai import OpenAI

from models.copywriting import OptimizedScriptResult, ScriptIdea, ScriptIdeaResult
from models.rubric import Rubric
from models.score import DimensionScores
from .base_client import BaseLLMClient


class DeepSeekClient(BaseLLMClient):
    """OpenAI-compatible client used by Moonshot/DeepSeek style APIs."""

    SCORE_KEYS = ("ER", "SR", "HP", "QL", "NA", "AB", "SAT")

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "moonshot-v1-8k",
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        if not api_key or api_key.startswith("your_"):
            raise ValueError("MOONSHOT_API_KEY is missing or still uses the placeholder value in .env.")
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _call_llm(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeError(
                f"LLM API call failed. base_url={self.base_url}, model={model or self.model}, error={exc}"
            ) from exc

        content = response.choices[0].message.content if response.choices else None
        if not content or not content.strip():
            raise RuntimeError("LLM API returned an empty message.")
        return content.strip()

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        if not response:
            raise ValueError("LLM response is empty; cannot parse JSON.")

        text = response.strip()
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"items": parsed}
        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "{[":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"items": parsed}

        preview = text[:500].replace("\n", " ")
        raise ValueError(f"LLM response is not valid JSON. First 500 chars: {preview}")

    def _numeric_scores_from_payload(self, payload: Dict[str, Any]) -> Dict[str, int]:
        source = payload.get("scores") if isinstance(payload.get("scores"), dict) else payload
        scores = {}
        missing_or_invalid = []
        for key in self.SCORE_KEYS:
            value = source.get(key) if isinstance(source, dict) else None
            try:
                numeric = int(round(float(value)))
            except (TypeError, ValueError):
                missing_or_invalid.append(f"{key}={value!r}")
                continue
            scores[key] = max(0, min(5, numeric))
        if missing_or_invalid:
            raise ValueError("Invalid numeric score fields: " + ", ".join(missing_or_invalid))
        return scores

    def _reasons_from_payload(self, payload: Dict[str, Any]) -> Dict[str, str]:
        raw_reasons = payload.get("reasons")
        if isinstance(raw_reasons, dict) and raw_reasons:
            return {key: str(raw_reasons.get(key, "")).strip() for key in self.SCORE_KEYS}

        if all(isinstance(payload.get(key), str) and payload.get(key).strip() for key in self.SCORE_KEYS):
            return {key: payload[key].strip() for key in self.SCORE_KEYS}

        raise ValueError("Missing reasons object keyed by ER/SR/HP/QL/NA/AB/SAT.")

    def _score_numbers_only(self, script: str, rubric: Rubric) -> Dict[str, int]:
        prompt = f"""Return JSON only.
Task: score this product/brand seeding short-video script.
Each value must be an integer from 0 to 5.

Rubric:
{rubric.format_rules()}

Script:
{script}

Return exactly this shape, with numbers only:
{{"ER":0,"SR":0,"HP":0,"QL":0,"NA":0,"AB":0,"SAT":0}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.1))
        return self._numeric_scores_from_payload(payload)

    def _score_reasons_only(self, script: str, scores: Dict[str, int]) -> Dict[str, str]:
        prompt = f"""Return JSON only.
Task: explain these scores for a product/brand seeding short-video script.
All string values must be Simplified Chinese. Keep each reason concise and actionable.

Scores:
{json.dumps(scores, ensure_ascii=False)}

Script:
{script}

Return exactly this shape:
{{
  "reasons": {{
    "ER": "",
    "SR": "",
    "HP": "",
    "QL": "",
    "NA": "",
    "AB": "",
    "SAT": ""
  }}
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.2))
        return self._reasons_from_payload(payload)

    def _score_and_reasons(self, script: str, rubric: Rubric) -> Dict[str, Any]:
        prompt = f"""Return JSON only.
Task: evaluate a product/brand seeding short-video script.
All score values must be integers from 0 to 5.
All reason strings must be Simplified Chinese.

Rubric:
{rubric.format_rules()}

Script:
{script}

Return exactly this shape:
{{
  "scores": {{"ER":0,"SR":0,"HP":0,"QL":0,"NA":0,"AB":0,"SAT":0}},
  "reasons": {{"ER":"","SR":"","HP":"","QL":"","NA":"","AB":"","SAT":""}}
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.2))

        try:
            scores = self._numeric_scores_from_payload(payload)
        except ValueError:
            scores = self._score_numbers_only(script, rubric)

        try:
            reasons = self._reasons_from_payload(payload)
        except ValueError:
            reasons = self._score_reasons_only(script, scores)

        return {"scores": scores, "reasons": reasons}

    def _storyboard(self, script: str, scores: Dict[str, int]) -> List[Dict[str, Any]]:
        prompt = f"""Return JSON only.
Task: create an executable storyboard for a product/brand seeding vertical short video.
All string values must be Simplified Chinese.
Generate 5 to 8 shots. The first 3 seconds must grab attention. The final shot must guide users to save, comment, buy, consult, or visit.

Beginner-friendly phone shooting rules:
- Do not use advanced film jargon such as focal length, three-point lighting, complex lens terms, or professional lighting setups.
- Every shot must be doable by one beginner holding a phone.
- Use plain instructions such as: 手机拿稳防抖, 利用窗边自然光, 画面保持明亮干净, 特写产品细节, 人物放在画面一侧, 先拍包装再拍使用效果, 前3秒节奏快一点, 音乐卡点展示.
- Give concrete phone actions, not vague aesthetic advice.

Scores:
{json.dumps(scores, ensure_ascii=False)}

Script:
{script}

Return exactly this shape:
{{
  "storyboard_guide": [
    {{
      "scene": "01 开场抓眼球",
      "duration_seconds": 6,
      "location": "",
      "shot_type": "手机近拍/手机远拍/商品特写/人物半身",
      "camera_movement": "手机保持稳定/缓慢靠近/横向平移/跟着手部动作拍",
      "description": "",
      "subject_action": "",
      "narration": "",
      "subtitle": "",
      "audio": "",
      "props": "",
      "execution_notes": ""
    }}
  ]
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.3))
        storyboard = payload.get("storyboard_guide") or payload.get("items") or payload.get("shots")
        if not storyboard and "scene" in payload:
            storyboard = [payload]
        if not isinstance(storyboard, list) or not storyboard:
            raise ValueError(f"LLM storyboard call returned no storyboard_guide. Fields: {', '.join(payload.keys())}")
        if len(storyboard) < 5:
            storyboard = self._expand_storyboard(script, scores, storyboard)
        return storyboard

    def _expand_storyboard(self, script: str, scores: Dict[str, int], current_storyboard: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prompt = f"""Return JSON only.
Task: expand this incomplete storyboard into 5 to 8 executable shots for a product/brand seeding vertical short video.
All string values must be Simplified Chinese.
Use beginner-friendly phone actions only. No advanced film jargon.

Scores:
{json.dumps(scores, ensure_ascii=False)}

Script:
{script}

Current incomplete storyboard:
{json.dumps(current_storyboard, ensure_ascii=False, indent=2)}

Return exactly this shape:
{{
  "storyboard_guide": [
    {{
      "scene": "01 开场抓眼球",
      "duration_seconds": 6,
      "location": "",
      "shot_type": "手机近拍/商品特写/人物半身",
      "camera_movement": "手机保持稳定/缓慢靠近/跟着手部动作拍",
      "description": "",
      "subject_action": "",
      "narration": "",
      "subtitle": "",
      "audio": "",
      "props": "",
      "execution_notes": ""
    }}
  ]
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.25))
        storyboard = payload.get("storyboard_guide") or payload.get("items") or payload.get("shots")
        if isinstance(storyboard, list) and len(storyboard) >= 5:
            return storyboard
        return current_storyboard

    def _shooting_guide(self, script: str, storyboard: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = f"""Return JSON only.
Task: create a beginner-friendly shooting-day guide for the storyboard below.
All string values must be Simplified Chinese.

Rules:
- Assume one person can shoot with a phone.
- Do not mention focal length, complex lighting methods, professional lens terms, or advanced cinematography jargon.
- Give practical actions: 利用窗边自然光, 手机保持稳定防抖, 背景收拾干净, 商品细节多拍两遍, 人物对半构图, 画面保持明亮干净, 前3秒节奏快一点抓眼球, 音乐卡点展示.
- Make it useful for a non-technical operator.

Script:
{script}

Storyboard:
{json.dumps(storyboard, ensure_ascii=False, indent=2)}

Return exactly this shape:
{{
  "shooting_guide": {{
    "lighting": "",
    "sound": "",
    "performance": "",
    "schedule": "",
    "location_plan": "",
    "equipment": "",
    "props": "",
    "crew": "",
    "cover_title": "",
    "platform_notes": "",
    "risk_notes": ""
  }}
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.25))
        guide = payload.get("shooting_guide") or payload.get("guide")
        guide_fields = {
            "lighting",
            "sound",
            "performance",
            "schedule",
            "location_plan",
            "equipment",
            "props",
            "crew",
            "cover_title",
            "platform_notes",
            "risk_notes",
        }
        if not guide and guide_fields.intersection(payload.keys()):
            guide = payload
        if not isinstance(guide, dict) or not guide:
            raise ValueError(f"LLM shooting guide call returned no shooting_guide. Fields: {', '.join(payload.keys())}")
        return guide

    def score_script(self, script: str, rubric: Rubric) -> Dict[str, Any]:
        score_payload = self._score_and_reasons(script, rubric)
        storyboard = self._storyboard(script, score_payload["scores"])
        shooting_guide = self._shooting_guide(script, storyboard)

        return {
            "scores": score_payload["scores"],
            "reasons": score_payload["reasons"],
            "storyboard_guide": storyboard,
            "shooting_guide": shooting_guide,
        }

    def generate_script_ideas(self, product_info: str) -> ScriptIdeaResult:
        prompt = f"""Return JSON only.
Task: generate 3 initial short-video scripts for product/brand seeding.
All string values must be Simplified Chinese.
The 3 styles must be: 走心, 反转, 直接促销.
Make the scripts口语化, easy to shoot with a phone, and suitable for short-video platforms.

Product or creative intent:
{product_info}

Return exactly this shape:
{{
  "ideas": [
    {{
      "style": "走心",
      "title": "",
      "hook": "",
      "script": "",
      "selling_points": ["", ""]
    }}
  ]
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.7))
        ideas = payload.get("ideas") or payload.get("items")
        if not isinstance(ideas, list) or not ideas:
            raise ValueError(f"LLM idea generation returned no ideas. Fields: {', '.join(payload.keys())}")
        return ScriptIdeaResult(ideas=[ScriptIdea.model_validate(item) for item in ideas[:3]])

    def optimize_script(self, original_script: str, score_context: Dict[str, Any]) -> OptimizedScriptResult:
        prompt = f"""Return JSON only.
Task: rewrite the original product/brand seeding script based on score weaknesses.
All string values must be Simplified Chinese.

Rewrite requirements:
- Keep the original meaning and core selling point.
- Fix the weak dimensions, such as low resonance, weak hook, unclear narrative, or lack of quotable lines.
- Make the result口语化, direct, high-retention, and high-share-potential.
- Add a stronger first-3-second hook.
- Make it practical for a short video creator to read or shoot.
- Do not invent unverifiable product claims.

Original script:
{original_script}

Score context:
{json.dumps(score_context, ensure_ascii=False, indent=2)}

Return exactly this shape:
{{
  "title": "",
  "optimized_script": "",
  "key_changes": ["", ""],
  "target_improvements": ["", ""]
}}
"""
        payload = self._parse_json_response(self._call_llm(prompt, temperature=0.55))
        if "optimized_script" not in payload:
            raise ValueError(f"LLM optimization returned no optimized_script. Fields: {', '.join(payload.keys())}")
        return OptimizedScriptResult.model_validate(payload)

    def analyze_counterfactual(self, script: str, scores: DimensionScores, composite: float, bucket: str) -> str:
        prompt = f"""Write a concise counterfactual analysis in Simplified Chinese.

Script summary:
{script[:500]}...

Scores: ER={scores.ER}, SR={scores.SR}, HP={scores.HP}, QL={scores.QL}, NA={scores.NA}, AB={scores.AB}, SAT={scores.SAT}
Composite: {composite:.2f}
Predicted bucket: {bucket}

Use this exact Chinese structure:
1. 如果爆（高播放）
   - 验证什么假设：
   - 推翻什么假设：
   - 可能新增什么维度：
2. 如果落在预期区间
   - 基准线验证什么：
3. 如果表现低于预期
   - 推翻什么核心判断：
4. 如果表现极差
   - 极端场景的可能解释：
"""
        return self._call_llm(prompt, temperature=0.5)

    def audit_bump(self, old_rubric: Rubric, new_rubric: Rubric, calibration_data: list) -> Dict[str, Any]:
        prompt = f"""Return JSON only. Audit whether the new rubric should replace the old one.
All string values must be Simplified Chinese.

Old formula: {old_rubric.current_version} - {old_rubric.versions[-1].formula if old_rubric.versions else "unknown"}
New formula: {new_rubric.current_version} - {new_rubric.versions[-1].formula if new_rubric.versions else "unknown"}

Calibration data:
{json.dumps(calibration_data, ensure_ascii=False, indent=2)}

Return:
{{
  "判定": "PASS 或 REJECT",
  "理由": "至少100字的详细分析",
  "关键风险": ["风险1", "风险2"]
}}
"""
        response = self._call_llm(prompt, temperature=0.3)
        try:
            return self._parse_json_response(response)
        except ValueError as exc:
            return {"判定": "REJECT", "理由": f"解析失败: {exc}", "关键风险": ["LLM返回格式错误"]}
