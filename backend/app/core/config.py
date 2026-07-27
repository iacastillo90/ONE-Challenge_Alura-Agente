import os
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError


class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    deepseek_api_key: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_base_url: str = ""
    openai_compatible_model: str = "gpt-4o-mini"

    vector_store_type: Literal["pgvector", "chroma", "qdrant"] = "pgvector"
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    embedding_provider: Literal["local", "api"] = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    log_level: str = "INFO"
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt_path: str = "./prompts/system.txt"
    llm_timeout_seconds: int = 60
    llm_retry_max_attempts: int = 3
    llm_retry_base_delay: float = 1.0

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    api_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_username: str = "admin"
    admin_password: str = "admin"

    max_upload_size_mb: int = 50
    max_chunks_per_document: int = 5000
    max_extracted_chars: int = 5_000_000
    retrieval_score_threshold: float = 0.45

    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent"

    storage_backend: Literal["local", "s3"] = "local"
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "agent-uploads"

    use_hybrid_search: bool = True
    hybrid_search_alpha: float = 0.7

    enable_feedback: bool = True
    enable_session_listing: bool = True

    token_limit_warning: int = 3000
    chunk_size: int = 512
    chunk_overlap: int = 64
    embedding_batch_size: int = 32

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    enable_registration: bool = True

    # Entorno de despliegue. Controla la seguridad de cookies, exposición de docs, etc.
    environment: Literal["development", "production"] = "development"
    # Cuando está vacío, se deriva del entorno (cookies seguras solo en producción).
    cookie_secure: bool | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Usuario de prueba / semilla para demostraciones. Las credenciales vienen de env (nunca codificadas)
    # pero por defecto usan la cuenta pública de demostración para que el challenge funcione de inmediato.
    # La contraseña se almacena con hash en la base de datos.
    demo_user_enabled: bool = True
    demo_username: str = "test@gmail.com"
    demo_password: str = "1234567890"

    # Orquestación con n8n + canal de WhatsApp
    n8n_webhook_secret: str = ""  # secreto compartido que n8n debe enviar para llamar a nuestros webhooks
    n8n_outbound_url: str = ""  # webhook de n8n al que enviamos peticiones POST para envíos de WhatsApp
    whatsapp_enabled: bool = False
    whatsapp_default_number: str = ""  # número de destino configurado en la plataforma

    public_url: str = "http://localhost:8000"

    @property
    def refresh_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment == "production"

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    otel_enabled: bool = True
    otel_service_name: str = "one-ai-agent"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_exporter_otlp_headers: str = ""
    otel_sample_rate: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @staticmethod
    def _parse_csv_list(v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v if isinstance(v, list) else [str(v)]

    @property
    def parsed_cors_origins(self) -> list[str]:
        return self._parse_csv_list(self.cors_origins)

    @property
    def parsed_allowed_hosts(self) -> list[str]:
        return self._parse_csv_list(self.allowed_hosts)


settings = Settings()

os.makedirs(Path(settings.system_prompt_path).parent, exist_ok=True)


def _validate_settings():
    is_prod = settings.environment == "production"
    # errors: siempre fatales. prod_errors: fatales solo en producción (valores por defecto seguros
    # son aceptables para desarrollo local / CI). warnings: informativos.
    errors: list[str] = []
    prod_errors: list[str] = []
    warnings: list[str] = []

    if settings.jwt_secret == "change-me-in-production":
        prod_errors.append("JWT_SECRET aún conserva el valor por defecto 'change-me-in-production' — defina una clave segura en producción")
    if settings.admin_username == "admin" and settings.admin_password == "admin":
        prod_errors.append("ADMIN_USERNAME/ADMIN_PASSWORD are using default credentials — change them in production")
    if settings.openai_compatible_base_url:
        parsed = urlparse(settings.openai_compatible_base_url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"OPENAI_COMPATIBLE_BASE_URL is not a valid URL: {settings.openai_compatible_base_url}")
        elif parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "metadata", "metadata.google.internal"):
            errors.append(f"OPENAI_COMPATIBLE_BASE_URL points to internal host ({parsed.hostname}) — SSRF risk")
    if not settings.database_url:
        errors.append("DATABASE_URL is empty — the app will crash on startup")
    if not settings.api_key:
        warnings.append("API_KEY is empty — X-API-Key auth is disabled (JWT still enforced). Set a strong API key for machine-to-machine access.")
    elif len(settings.api_key) < 16:
        warnings.append("API_KEY is too short — use at least 16 characters")

    if settings.demo_user_enabled and is_prod:
        warnings.append("DEMO_USER_ENABLED is true in production — disable it or the demo account will be publicly usable")
    if settings.whatsapp_enabled and not settings.n8n_webhook_secret:
        prod_errors.append("WHATSAPP_ENABLED is true but N8N_WEBHOOK_SECRET is empty — webhooks would be unauthenticated")
    if settings.storage_backend == "s3" and not (settings.s3_access_key and settings.s3_secret_key):
        prod_errors.append("STORAGE_BACKEND=s3 requires S3_ACCESS_KEY and S3_SECRET_KEY")
    if settings.whatsapp_enabled and settings.n8n_webhook_secret and len(settings.n8n_webhook_secret) < 16:
        warnings.append("N8N_WEBHOOK_SECRET is short — use at least 16 characters")

    if is_prod:
        errors.extend(prod_errors)
    else:
        warnings.extend(prod_errors)

    for w in warnings:
        logger.warning(f"Configuration: {w}")
    if errors:
        for e in errors:
            logger.critical(f"CONFIGURATION ERROR: {e}")
        raise ConfigurationError("; ".join(errors))


try:
    _validate_settings()
except ConfigurationError:
    logger.critical("Fatal configuration errors detected — fix them before starting")
    sys.exit(1)
