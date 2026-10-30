from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """App configuration, read from environment variables or the repo-root .env file."""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://family:family@localhost:5434/family_finances"
    # Secure cookies are only sent over HTTPS. Turn off for plain-HTTP development from a phone
    # on the LAN; browsers already accept them on http://localhost.
    session_cookie_secure: bool = True


settings = Settings()
