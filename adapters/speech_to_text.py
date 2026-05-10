from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import dashscope
from dashscope.audio.asr import Recognition


class SpeechToText(ABC):
    @abstractmethod
    def transcribe(self, audio_file: str) -> str:
        pass


class DashScopeTranscriber(SpeechToText):
    def __init__(
        self,
        api_key: str,
        model_name: str = "paraformer-realtime-v2",
        sample_rate: int = 16000,
    ):
        if not api_key or api_key.startswith("your_"):
            raise ValueError("DASHSCOPE_API_KEY is missing or still uses the placeholder value.")
        self.api_key = api_key
        self.model_name = model_name
        self.sample_rate = sample_rate
        dashscope.api_key = api_key

    def transcribe(self, audio_file: str) -> str:
        path = Path(audio_file)
        if not path.exists():
            raise FileNotFoundError(f"Uploaded media file does not exist: {path}")
        if path.stat().st_size == 0:
            raise ValueError("Uploaded media file is empty.")

        audio_format = self._format_from_suffix(path.suffix)
        try:
            recognition = Recognition(
                model=self.model_name,
                format=audio_format,
                sample_rate=self.sample_rate,
                callback=None,
            )
            response = recognition.call(str(path))
        except Exception as exc:
            raise RuntimeError(f"DashScope transcription request failed: {exc}") from exc

        if getattr(response, "status_code", None) != 200:
            message = getattr(response, "message", "") or getattr(response, "code", "")
            raise RuntimeError(f"DashScope transcription failed: {message}")

        transcript = self._extract_text(response)
        if not transcript:
            raise RuntimeError("DashScope transcription succeeded but returned empty text.")
        return transcript

    def _format_from_suffix(self, suffix: str) -> str:
        value = suffix.lower().lstrip(".")
        aliases = {"m4a": "mp4", "aac": "aac", "mp4": "mp4", "mov": "mp4"}
        return aliases.get(value, value or "mp3")

    def _extract_text(self, response: Any) -> str:
        if hasattr(response, "get_sentence"):
            sentence = response.get_sentence()
        else:
            sentence = getattr(response, "output", {}).get("sentence")

        if isinstance(sentence, list):
            return "\n".join(item.get("text", "") for item in sentence if isinstance(item, dict)).strip()
        if isinstance(sentence, dict):
            return str(sentence.get("text", "")).strip()

        output = getattr(response, "output", None)
        if isinstance(output, dict):
            return str(output.get("text") or output.get("transcription") or "").strip()
        return ""


def create_transcriber(provider: str, api_key: str = None, model_name: str = "paraformer-realtime-v2") -> SpeechToText:
    if provider == "dashscope":
        return DashScopeTranscriber(api_key, model_name=model_name)
    raise ValueError(f"Unsupported speech-to-text provider: {provider}")
