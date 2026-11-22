from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        load_dotenv(BASE_DIR / ".env", override=True)
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()

        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip()

        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1").strip()

        self.llm_provider: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()

        self.deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "").strip()
        self.deepgram_model: str = os.getenv("DEEPGRAM_MODEL", "nova-3").strip()

        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
        self.groq_whisper_model: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo").strip()

        self.elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()

        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "").strip()

        db_path = os.getenv("DATABASE_PATH", str(BASE_DIR / "rehearse.db")).strip()
        self.database_path: Path = Path(db_path) if os.path.isabs(db_path) else (BASE_DIR / db_path)
        self.frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()

    def active_llm_info(self) -> tuple[str, str]:
        if self.llm_provider == "gemini" and self.gemini_api_key:
            return ("gemini", self.gemini_model)
        if self.llm_provider == "anthropic" and self.anthropic_api_key:
            return ("anthropic", self.anthropic_model)
        if self.llm_provider == "openai" and self.openai_api_key:
            return ("openai", self.openai_model)

        if self.gemini_api_key:
            return ("gemini", self.gemini_model)
        if self.anthropic_api_key:
            return ("anthropic", self.anthropic_model)
        if self.openai_api_key:
            return ("openai", self.openai_model)
        return ("local_coach", "deterministic-rubric-v1")

    def active_stt_info(self) -> tuple[str, str]:
        if self.deepgram_api_key:
            return ("deepgram", self.deepgram_model)
        if self.openai_api_key:
            return ("openai_whisper", "whisper-1")
        if self.groq_api_key:
            return ("groq_whisper", self.groq_whisper_model)
        if self.gemini_api_key:
            return ("gemini_audio", "gemini-3.5-transcribe")
        return ("browser_live", "web-speech-verbatim")

    def active_tts_info(self) -> tuple[str, str]:
        if self.elevenlabs_api_key:
            return ("elevenlabs", "eleven_multilingual_v2")
        if self.openai_api_key:
            return ("openai_tts", "tts-1")
        return ("browser_speech", "web-speech-synthesis")

    def update_runtime_keys(self, updates: dict[str, str]) -> None:
        env_path = BASE_DIR / ".env"
        existing: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    existing[k.strip()] = v.strip()

        allowed = {
            "GEMINI_API_KEY", "GEMINI_MODEL",
            "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
            "OPENAI_API_KEY", "OPENAI_MODEL",
            "LLM_PROVIDER",
            "DEEPGRAM_API_KEY", "DEEPGRAM_MODEL",
            "GROQ_API_KEY", "ELEVENLABS_API_KEY", "TAVILY_API_KEY",
        }
        for k, v in updates.items():
            if k in allowed and v is not None:
                val = v.strip()
                existing[k] = val
                os.environ[k] = val

        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.reload()


settings = Settings()
