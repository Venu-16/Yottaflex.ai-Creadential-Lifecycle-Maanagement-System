from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    credential_signing_private_key: str | None = None
    credential_signing_issuer_code: str | None = None
    credential_signing_key_id: str | None = None
    demo_user_principal_key: str | None = None
    demo_user_password: str | None = None
    demo_user_role: str | None = None
    demo_user_display_name: str | None = None
    full_dataset_manifest_path: str | None = None
    full_dataset_import_report_path: str | None = None
    full_dataset_validation_report_path: str | None = None
    full_dataset_verification_report_path: str | None = None
    api_performance_report_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 bytes.")
        if any(marker in value.lower() for marker in ("replace-with", "change-me", "your-secret")):
            raise ValueError("SECRET_KEY must not use a documented placeholder value.")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256.")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_lifetime(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive.")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins, not '*'.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
