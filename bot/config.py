import re
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = BOT_DIR.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    backend_base_url: str = Field(default="http://localhost:8000", alias="BACKEND_BASE_URL")
    backend_api_token: str = Field(alias="BACKEND_API_TOKEN")
    admin_ids_raw: str = Field(default="", alias="BOT_ADMIN_IDS")
    super_admin_ids_raw: str = Field(default="", alias="BOT_SUPER_ADMIN_IDS")

    @staticmethod
    def _parse_ids(raw_ids: str) -> set[int]:
        result: set[int] = set()
        for chunk in re.split(r"[\s,;]+", raw_ids):
            stripped = chunk.strip()
            if not stripped:
                continue
            try:
                result.add(int(stripped))
            except ValueError:
                continue
        return result

    @property
    def admin_ids(self) -> set[int]:
        return self._parse_ids(self.admin_ids_raw)

    @property
    def super_admin_ids(self) -> set[int]:
        parsed = self._parse_ids(self.super_admin_ids_raw)
        if parsed:
            return parsed
        # Backward compatibility: if BOT_SUPER_ADMIN_IDS is not set,
        # BOT_ADMIN_IDS is treated as main admins.
        return self.admin_ids


def load_settings() -> Settings:
    return Settings()
