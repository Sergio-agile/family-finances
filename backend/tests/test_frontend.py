import pytest

from app.main import API_HEADERS, app, serve_frontend

INDEX = "<!doctype html><title>Family Finances</title>"
FRONTEND_CSP = (
    "default-src 'self'; base-uri 'none'; form-action 'self'; "
    "frame-ancestors 'none'; object-src 'none'"
)


@pytest.fixture
def frontend(tmp_path):
    """A minimal `npm run build` output, served the way production serves it."""
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log('hi')")
    serve_frontend(app, tmp_path)
    yield
    app.router.routes.pop()  # the mount added above


@pytest.mark.usefixtures("frontend")
def test_serves_the_page_with_its_own_policy(anonymous_client):
    response = anonymous_client.get("/")

    assert response.status_code == 200
    assert response.text == INDEX
    assert response.headers["Content-Security-Policy"] == FRONTEND_CSP
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.usefixtures("frontend")
def test_caches_hashed_assets_for_a_year(anonymous_client):
    response = anonymous_client.get("/assets/index-abc123.js")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert response.headers["Content-Security-Policy"] == FRONTEND_CSP


@pytest.mark.usefixtures("frontend")
def test_the_api_keeps_its_routes_and_headers(anonymous_client):
    response = anonymous_client.get("/api/health")

    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["Content-Security-Policy"] == API_HEADERS["Content-Security-Policy"]


@pytest.mark.usefixtures("frontend")
def test_an_unknown_api_path_is_a_json_404_not_the_page(anonymous_client):
    response = anonymous_client.get("/api/nope")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.usefixtures("frontend")
def test_cannot_read_files_outside_the_build(anonymous_client):
    assert anonymous_client.get("/..%2F..%2Fetc%2Fpasswd").status_code == 404
