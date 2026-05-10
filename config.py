from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def read_streamlit_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        import streamlit as st

        if name in st.secrets:
            value = st.secrets[name]
            return str(value) if value is not None else default
    except Exception:
        pass
    return default


class Settings(BaseSettings):
    MOONSHOT_API_KEY: str = Field(default_factory=lambda: read_streamlit_secret("MOONSHOT_API_KEY", "") or "")
    MOONSHOT_BASE_URL: str = "https://api.moonshot.cn/v1"
    MOONSHOT_MODEL: str = "moonshot-v1-8k"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 2
    
    DASHSCOPE_API_KEY: str = Field(default_factory=lambda: read_streamlit_secret("DASHSCOPE_API_KEY", "") or "")
    DASHSCOPE_ASR_MODEL: str = Field(
        default_factory=lambda: read_streamlit_secret("DASHSCOPE_ASR_MODEL", "paraformer-realtime-v2")
        or "paraformer-realtime-v2"
    )
    SUPABASE_URL: str = Field(default_factory=lambda: read_streamlit_secret("SUPABASE_URL", "") or "")
    SUPABASE_KEY: str = Field(default_factory=lambda: read_streamlit_secret("SUPABASE_KEY", "") or "")
    
    PREDICTIONS_DIR: str = "./predictions"
    SCRIPTS_DIR: str = "./scripts"
    EXPORTS_DIR: str = "./exports"
    RUBRIC_FILE: str = "./rubric_notes.md"
    STATE_FILE: str = "./.cheat-state.json"
    
    SPEECH_TO_TEXT_PROVIDER: str = "dashscope"
    WHISPER_MODEL: str = "base"
    
    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"

settings = Settings()
