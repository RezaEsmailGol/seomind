from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8787
    data_dir: Path = Path(".seomind")
    frontend_url: str = "http://127.0.0.1:3000"
    oauth_redirect_uri: str = "http://127.0.0.1:8787/api/google/oauth/callback"
    log_level: str = "info"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"

    daily_check_enabled: bool = True
    daily_check_hour: int = 9
    daily_check_interval_minutes: int = 15
    daily_crawl_pages: int = 25
    daily_language: str = "en"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SEOMIND_",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
