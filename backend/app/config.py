"""アプリケーション設定"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    REINFOLIB_API_KEY: str = os.getenv("REINFOLIB_API_KEY", "")
    REINFOLIB_BASE_URL: str = "https://www.reinfolib.mlit.go.jp/ex-api/external"

    # LLM設定
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://localhost:8001/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "")  # 空=自動検出
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "120"))
    LLM_MAX_TOKENS_YOUKAI: int = int(os.getenv("LLM_MAX_TOKENS_YOUKAI", "1024"))
    LLM_MAX_TOKENS_DEFAULT: int = int(os.getenv("LLM_MAX_TOKENS_DEFAULT", "512"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # TTS設定（VOICEVOX）
    TTS_ENABLED: bool = os.getenv("TTS_ENABLED", "true").lower() in ("true", "1", "yes")
    TTS_API_URL: str = os.getenv("TTS_API_URL", "http://localhost:50021")
    TTS_TIMEOUT: float = float(os.getenv("TTS_TIMEOUT", "30"))
    TTS_CACHE_MAX_SIZE: int = int(os.getenv("TTS_CACHE_MAX_SIZE", "100"))

    # CORS設定（サブドメイン対応）
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
