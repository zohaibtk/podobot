from fastapi.testclient import TestClient

from app.main import create_app


def test_security_and_correlation_headers_are_present() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "test-correlation"})

    assert response.headers["X-Correlation-ID"] == "test-correlation"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_docs_content_security_policy_allows_docs_assets() -> None:
    client = TestClient(create_app())

    response = client.get("/docs")

    assert response.status_code == 200
    policy = response.headers["Content-Security-Policy"]
    assert "https://cdn.jsdelivr.net" in policy
    assert "frame-ancestors 'none'" in policy
