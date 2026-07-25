from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    deepseek_api_key: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_base_url: str = ""

    vector_store_type: Literal["chroma", "qdrant"] = "chroma"
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    embedding_provider: Literal["local", "api"] = "local"
    embedding_model: str = "all-MiniLM-L6-v2"

    log_level: str = "INFO"
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt_path: str = "./prompts/system.txt"

    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
