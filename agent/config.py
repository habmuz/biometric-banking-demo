from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-opus-4-6"

    # Keycloak
    keycloak_base_url: str = "http://localhost:8080"
    keycloak_realm: str = "biometric-banking"
    keycloak_client_id: str = "biometric-agent"
    keycloak_client_secret: str = "change-this-in-production"

    # Liveness thresholds (MAS ISO 30107-3 PAD Level 2)
    liveness_threshold: float = 0.85
    deepfake_threshold: float = 0.15
    max_auth_attempts: int = 5

    # InsightFace
    insightface_model: str = "buffalo_l"
    insightface_ctx_id: int = -1  # -1 = CPU; set 0 for GPU

    # Langfuse observability (optional — leave blank to disable)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Face template DB
    face_db_path: str = "data/face_templates.db"
    face_similarity_threshold: float = 0.35

    # Audit log
    audit_log_path: str = "audit.jsonl"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
