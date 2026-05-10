import os
import re
from datetime import datetime
from pathlib import Path
from models.prediction import BucketDistribution, Prediction
from models.score import DimensionScores, ScoreResult

class FileStorage:
    
    def __init__(self, predictions_dir: str, scripts_dir: str):
        self.predictions_dir = Path(predictions_dir)
        self.scripts_dir = Path(scripts_dir)
        self.predictions_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
    
    def save_prediction(self, prediction: Prediction) -> str:
        filename = f"{prediction.prediction_time.strftime('%Y-%m-%d')}_{prediction.article_id}.md"
        filepath = self.predictions_dir / filename
        content = prediction.to_markdown()
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)
    
    def load_prediction(self, article_id: str) -> Prediction:
        for filepath in self.predictions_dir.glob(f"*_{article_id}.md"):
            content = filepath.read_text(encoding='utf-8')
            return self._parse_prediction(content)
        return None
    
    def _parse_prediction(self, content: str) -> Prediction:
        def find(pattern: str, default: str = "") -> str:
            match = re.search(pattern, content, flags=re.MULTILINE)
            return match.group(1).strip() if match else default

        def find_float(pattern: str, default: float = 0.0) -> float:
            try:
                return float(find(pattern, str(default)))
            except ValueError:
                return default

        score_match = re.search(
            r"ER\s*(\d+)\s*/\s*SR\s*(\d+)\s*/\s*HP\s*(\d+)\s*/\s*QL\s*(\d+)\s*/\s*NA\s*(\d+)\s*/\s*AB\s*(\d+)\s*/\s*SAT\s*(\d+)",
            content,
        )
        score_values = {}
        if score_match:
            score_values = dict(zip(["ER", "SR", "HP", "QL", "NA", "AB", "SAT"], [int(value) for value in score_match.groups()]))
        scores = DimensionScores.from_dict(score_values)
        composite = find_float(r"composite=\*\*([0-9.]+)\*\*")

        distributions = []
        for bucket, probability in re.findall(r"-\s*`([^`]+)`\s*->\s*(\d+)%", content):
            distributions.append(BucketDistribution(bucket=bucket, probability=float(probability) / 100))
        if not distributions:
            bucket = find(r"\*\*Bucket\*\*:\s*`?([^`\n]+)`?", "unknown")
            distributions = [BucketDistribution(bucket=bucket, probability=1.0)]

        prediction_time_text = find(r"\*\*.*?\*\*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})")
        try:
            prediction_time = datetime.strptime(prediction_time_text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            prediction_time = datetime.now()

        return Prediction(
            article_id=find(r"\*\*Article ID\*\*:\s*(.+)") or "unknown",
            title=find(r"\*\*Title\*\*:\s*(.+)") or "prediction",
            script_path=find(r"\*\*Script Path\*\*:\s*(.+)"),
            script_hash=find(r"\*\*Script Hash\*\*:\s*(.+)"),
            rubric_version=find(r"\*\*Rubric Version\*\*:\s*\*\*(.+?)\*\*", "v2"),
            prediction_time=prediction_time,
            score_result=ScoreResult(scores=scores, composite=composite, reasons={}, storyboard_guide=[], shooting_guide=None),
            bucket=find(r"\*\*Bucket\*\*:\s*`?([^`\n]+)`?", distributions[0].bucket),
            center=find_float(r"\*\*.*?\*\*:\s*([0-9.]+)w"),
            distribution=distributions,
            confidence=find(r"\*\*Confidence\*\*:\s*(.+)", "unknown"),
            scored_by=find(r"\*\*Scored By\*\*:\s*(.+)", "system"),
            user_override=find(r"\*\*User Override\*\*:\s*(.+)", "none"),
        )
    
    def list_predictions(self) -> list:
        predictions = []
        for filepath in self.predictions_dir.glob("*.md"):
            predictions.append({
                'path': str(filepath),
                'name': filepath.name,
                'modified': datetime.fromtimestamp(filepath.stat().st_mtime)
            })
        return sorted(predictions, key=lambda x: x['modified'], reverse=True)
    
    def save_script(self, content: str, title: str) -> str:
        timestamp = datetime.now().strftime('%Y-%m-%d')
        short_title = title[:20].replace(' ', '_').replace('/', '_')
        filename = f"{timestamp}_{short_title}.md"
        filepath = self.scripts_dir / filename
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)
    
    def load_script(self, filepath: str) -> str:
        return Path(filepath).read_text(encoding='utf-8')
    
    def list_scripts(self) -> list:
        scripts = []
        for filepath in self.scripts_dir.glob("*.md"):
            scripts.append({
                'path': str(filepath),
                'name': filepath.name,
                'modified': datetime.fromtimestamp(filepath.stat().st_mtime)
            })
        return sorted(scripts, key=lambda x: x['modified'], reverse=True)
