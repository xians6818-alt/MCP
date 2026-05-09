import os
from datetime import datetime
from pathlib import Path
from models.prediction import Prediction

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
        pass
    
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
