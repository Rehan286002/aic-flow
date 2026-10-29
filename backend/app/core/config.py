from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AIC-Flow API"
    app_env: str = "local"

    database_url: str
    redis_url: str

    # Authentication & JWT Configuration
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "aic-flow"
    jwt_audience: str = "aic-flow-api"
    access_token_expire_minutes: int = Field(default=30, gt=0)

    # CORS & Cookie Transport Configuration
    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]
    access_cookie_name: str = "aic_flow_access"
    csrf_cookie_name: str = "aic_flow_csrf"
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_secure: bool | None = None
    cookie_domain: str | None = None

    # Storage & Document Pipeline Configuration
    storage_root_dir: str = Field(default=str(BACKEND_ROOT.parent / "storage"))
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024)  # 20 MB
    max_pdf_pages: int = Field(default=200, gt=0)
    max_image_dimension: int = Field(default=10000, gt=0)
    max_image_pixels: int = Field(default=40_000_000, gt=0)
    ocr_render_dpi: int = Field(default=200, ge=72, le=600)
    ocr_min_native_chars_per_page: int = Field(default=30, ge=0)
    ocr_processing_timeout_seconds: float = Field(default=60.0, gt=0.0)

    # Antivirus / Malware Scanner Configuration
    malware_scanner_type: Literal["clamav", "mock"] = "clamav"
    clamav_host: str = "127.0.0.1"
    clamav_port: int = 3310
    clamav_timeout_seconds: float = 20.0

    @property
    def is_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env.lower() == "production"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def JWT_SECRET_KEY(self) -> SecretStr | None:
        return self.jwt_secret_key

    @property
    def JWT_ALGORITHM(self) -> str:
        return self.jwt_algorithm

    @property
    def JWT_ISSUER(self) -> str:
        return self.jwt_issuer

    @property
    def JWT_AUDIENCE(self) -> str:
        return self.jwt_audience

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.access_token_expire_minutes


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
