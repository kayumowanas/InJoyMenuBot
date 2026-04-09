from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = BACKEND_DIR.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    app_name: str = Field(default="InJoy Menu API", alias="BACKEND_NAME")
    debug: bool = Field(default=False, alias="BACKEND_DEBUG")
    address: str = Field(default="0.0.0.0", alias="BACKEND_ADDRESS")
    port: int = Field(default=8000, alias="BACKEND_PORT")
    reload: bool = Field(default=False, alias="BACKEND_RELOAD")

    api_token: str = Field(default="dev-token", alias="BACKEND_API_TOKEN")
    sqlite_path: str = Field(default="./data/injoy.db", alias="BACKEND_SQLITE_PATH")


settings = Settings.model_validate({})
