import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize(
    ("method", "path", "headers", "expected_status"),
    [
        ("get", "/api/health", {}, 200),
        ("get", "/api/auth/me", {}, 401),
        ("post", "/api/auth/logout", {"Origin": "https://evil.example"}, 403),
    ],
)
def test_every_response_carries_the_security_headers(
    anonymous_client, method, path, headers, expected_status
):
    response = anonymous_client.request(method, path, headers=headers)

    assert response.status_code == expected_status
    assert response.headers["Cache-Control"] == "no-store"
    assert (
        response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    )
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_no_hsts_outside_production(anonymous_client):
    # HSTS would make browsers refuse plain HTTP to this host for two years.
    assert "Strict-Transport-Security" not in anonymous_client.get("/api/health").headers


SAFE_PRODUCTION = {
    "environment": "production",
    "session_cookie_secure": True,
    "app_url": "https://finanzas.example.com",
    "allowed_hosts": ["finanzas.example.com"],
}


def production_settings(**changes) -> Settings:
    # _env_file=None: only what the test passes, never the developer's .env.
    return Settings(_env_file=None, **SAFE_PRODUCTION | changes)


def test_accepts_a_safe_production_configuration():
    assert production_settings().is_production


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"session_cookie_secure": False}, "SESSION_COOKIE_SECURE must be true"),
        ({"app_url": "http://finanzas.example.com"}, "APP_URL must use https://"),
        ({"allowed_hosts": ["*"]}, "ALLOWED_HOSTS must list the real domains"),
    ],
)
def test_refuses_to_start_with_unsafe_production_settings(changes, problem):
    with pytest.raises(ValidationError, match=problem):
        production_settings(**changes)


def test_development_allows_relaxed_settings():
    settings = Settings(_env_file=None, session_cookie_secure=False, app_url="http://localhost")

    assert not settings.is_production
