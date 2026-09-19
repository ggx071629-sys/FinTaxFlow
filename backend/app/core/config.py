from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://fintax:fintax@127.0.0.1:5432/fintaxflow"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_hours: int = 12
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    pdf_dir: Path = REPO_DIR / "var" / "invoice-pdfs"
    simulation_base_url: str = "http://127.0.0.1:8000"
    rpa_browser_channel: str = "chrome"
    rpa_evidence_dir: Path = REPO_DIR / "var" / "rpa-runs"
    processor_enabled: bool = True
    billing_process_delay_seconds: float = 1.5
    processor_poll_seconds: float = 0.4
    processor_lock_key: int = 746201

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
