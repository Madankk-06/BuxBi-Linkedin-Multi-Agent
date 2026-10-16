import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # LLM Provider
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Database Configuration (MySQL / SQLite)
    DB_TYPE: str = os.getenv("DB_TYPE", "mysql").lower()
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "linkedin_agent")

    # LinkedIn / Publora
    PUBLORA_API_KEY: str = os.getenv("PUBLORA_API_KEY", "")
    LINKEDIN_PLATFORM_ID: str = os.getenv("LINKEDIN_PLATFORM_ID", "")

    # Automation
    SCHEDULE_TIME: str = os.getenv("SCHEDULE_TIME", "07:30")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    MAX_DAILY_CONNECTIONS: int = int(os.getenv("MAX_DAILY_CONNECTIONS", "3"))

    # Local data fallback
    DATA_DIR = BASE_DIR / "data"
    SQLITE_PATH = DATA_DIR / "agent.db"

    @classmethod
    def validate(cls) -> list[str]:
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        
        if cls.LLM_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        elif cls.LLM_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        elif cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        elif cls.LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
            
        return missing

config = Config()
