"""
Application configuration.

Centralizes all runtime configuration (paths, secret keys, JWT params,
database URL, CORS, upload limits). Values can be overridden via
environment variables or a .env file in production.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ---- General
    app_name: str = "SingleCellX FYP"
    app_version: str = "1.0.0"
    debug: bool = True

    # ---- Storage
    upload_dir: Path = BASE_DIR / "uploads"
    storage_dir: Path = BASE_DIR / "storage"
    max_upload_size_mb: int = 100

    # ---- Database
    database_url: str = f"sqlite:///{BASE_DIR / 'singlecellx.db'}"

    # ---- Security / JWT
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 h

    # ---- CORS
    allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
        "*",  # Dev only — restrict in production
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Ensure directories exist on import
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.storage_dir.mkdir(parents=True, exist_ok=True)
