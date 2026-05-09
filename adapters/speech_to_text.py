from abc import ABC, abstractmethod
import dashscope

class SpeechToText(ABC):
    
    @abstractmethod
    def transcribe(self, audio_file: str) -> str:
        pass

class DashScopeTranscriber(SpeechToText):
    
    def __init__(self, api_key: str):
        dashscope.api_key = api_key
    
    def transcribe(self, audio_file: str) -> str:
        try:
            response = dashscope.asr.SpeechRecognizer.call(
                model=dashscope.asr.Models.vosk_zh_cn,
                audio_file=audio_file,
                format='mp3'
            )
            if response.status_code == 200:
                return response.output.result.transcription
            raise Exception(f"转录失败: {response.message}")
        except Exception as e:
            raise RuntimeError(f"DashScope转录错误: {str(e)}")

def create_transcriber(provider: str, api_key: str = None, model_name: str = "base") -> SpeechToText:
    if provider == "dashscope":
        if not api_key:
            raise ValueError("DashScope需要API密钥")
        return DashScopeTranscriber(api_key)
    else:
        raise ValueError(f"不支持的语音转文字提供商: {provider}")
