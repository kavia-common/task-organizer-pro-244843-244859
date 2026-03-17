import os
from dataclasses import dataclass
from typing import List, Optional


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # Server
    host: str
    port: int
    trust_proxy: bool

    # CORS
    allowed_origins: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    cors_max_age: int

    # Auth
    jwt_secret: str
    jwt_algorithm: str
    access_token_exp_minutes: int

    # Database
    database_url: str


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load settings from environment variables.

    Environment variables expected:
    - ALLOWED_ORIGINS (csv)
    - ALLOWED_METHODS (csv)
    - ALLOWED_HEADERS (csv)
    - CORS_MAX_AGE (int)
    - TRUST_PROXY (bool)
    - PORT (int)
    - JWT_SECRET (string)  <-- required for production
    - JWT_ALGORITHM (string, default HS256)
    - ACCESS_TOKEN_EXPIRES_MINUTES (int)
    - DATABASE_URL (PostgreSQL URL)
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    trust_proxy = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes", "on")

    allowed_origins = _split_csv(os.getenv("ALLOWED_ORIGINS")) or ["*"]
    allowed_methods = _split_csv(os.getenv("ALLOWED_METHODS")) or ["*"]
    allowed_headers = _split_csv(os.getenv("ALLOWED_HEADERS")) or ["*"]
    cors_max_age = int(os.getenv("CORS_MAX_AGE", "3600"))

    # NOTE: Orchestrator should provide JWT_SECRET in .env for real deployments.
    jwt_secret = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_exp_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "60"))

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        # Fallback to the known local dev connection if DATABASE_URL isn't set.
        # In deployment, DATABASE_URL must be set (do not rely on this).
        database_url = "postgresql://appuser:dbuser123@localhost:5000/myapp"

    return Settings(
        host=host,
        port=port,
        trust_proxy=trust_proxy,
        allowed_origins=allowed_origins,
        allowed_methods=allowed_methods,
        allowed_headers=allowed_headers,
        cors_max_age=cors_max_age,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        access_token_exp_minutes=access_token_exp_minutes,
        database_url=database_url,
    )
