"""Application settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://livocrm_user:supersecretpassword@db:5432/livocrm"

    # ── Auth / JWT ──
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Redis ──
    REDIS_URL: str = "redis://redis:6379/0"

    # ── AWS (for AI features) ──
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    BEDROCK_LLM_MODEL: str = "us.meta.llama4-scout-17b-instruct-v1:0"
    BEDROCK_ENABLED: bool = True
    BEDROCK_MAX_TOKENS: int = 220
    BEDROCK_TEMPERATURE: float = 0.2


settings = Settings()
