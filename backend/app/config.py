"""Application settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Database ──
    DATABASE_URL: str = ""  # Must be provided via .env

    # ── Auth / JWT ──
    SECRET_KEY: str = ""  # Must be provided via .env (minimum 32 chars)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_NAME: str = "livocrm_session"
    ALLOW_REGISTRATION: bool = True

    # ── Redis ──
    REDIS_URL: str = "redis://redis:6379/0"

    # ── HTTP ──
    # Comma-separated browser origins allowed by CORS (nginx serves the SPA same-origin)
    CORS_ORIGINS: str = "http://localhost:3500,http://localhost:5173"
    # Serve /api/docs and /api/openapi.json only when explicitly enabled
    ENABLE_DOCS: bool = False
    LOG_LEVEL: str = "INFO"

    # ── LLM provider ──
    # "groq" (default) or "bedrock" (legacy, needs AWS credentials)
    LLM_PROVIDER: str = "groq"
    # One key, or several comma-separated keys that are load-balanced (see services/llm/key_pool.py).
    GROQ_API_KEYS: str = ""
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL_FAST: str = "openai/gpt-oss-20b"
    GROQ_MODEL_SMART: str = "openai/gpt-oss-120b"
    LLM_TIMEOUT_S: float = 15.0
    LLM_TEMPERATURE: float = 0.2

    # ── Recovery engine ──
    # In-process loop that generates follow-up tasks every 60 s (off by default; tests never enable it)
    ENABLE_SCHEDULER: bool = False

    # ── AWS (legacy Bedrock provider) ──
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    BEDROCK_LLM_MODEL: str = "us.meta.llama4-scout-17b-instruct-v1:0"
    BEDROCK_ENABLED: bool = True
    BEDROCK_MAX_TOKENS: int = 220
    BEDROCK_TEMPERATURE: float = 0.2

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

# Validate required settings at startup
if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be provided via .env and be at least 32 characters long")

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL must be provided via .env")
