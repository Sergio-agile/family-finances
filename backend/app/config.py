from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """App configuration, read from environment variables or the repo-root .env file."""

    # hide_input_in_errors: a startup error must not print DATABASE_URL (and its password).
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", extra="ignore", hide_input_in_errors=True
    )

    database_url: str = "postgresql+psycopg://family:family@localhost:5434/family_finances"
    # Secure cookies are only sent over HTTPS. Turn off for plain-HTTP development from a phone
    # on the LAN; browsers already accept them on http://localhost.
    session_cookie_secure: bool = True
    # Where the frontend is served, for links printed from the command line.
    app_url: str = "http://localhost:5173"
    environment: Literal["development", "production"] = "development"
    # Host headers the API answers to, as JSON: ALLOWED_HOSTS='["finanzas.example.com"]'.
    # Any host in development, so the phone can use the computer's LAN address.
    allowed_hosts: list[str] = ["*"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def refuse_unsafe_production(self) -> Self:
        """Fail at startup, not in front of users, if production is configured like development."""
        if self.is_production:
            problems = [
                message
                for unsafe, message in [
                    (not self.session_cookie_secure, "SESSION_COOKIE_SECURE must be true"),
                    (not self.app_url.startswith("https://"), "APP_URL must use https://"),
                    ("*" in self.allowed_hosts, "ALLOWED_HOSTS must list the real domains"),
                ]
                if unsafe
            ]
            if problems:
                raise ValueError("Unsafe production settings: " + "; ".join(problems))
        return self


settings = Settings()
