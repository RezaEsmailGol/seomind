from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8787
    data_dir: Path = Path(".seomind")
    log_level: str = "info"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SEOMIND_",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
