"""Auth dependency tests (offline — no Supabase network calls)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import verify_token


def test_verify_token_rejects_malformed_without_network():
    with pytest.raises(ValueError):
        verify_token("not-a-token")


def test_jwks_client_helper_returns_client_not_itself(monkeypatch):
    """Regression test: the cached JWKS helper must return a PyJWKClient."""
    import app.services.auth as auth_module

    monkeypatch.setattr(auth_module, "_jwks_client_instance", None)
    created = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            created.append((args, kwargs))

    monkeypatch.setattr(auth_module.jwt, "PyJWKClient", FakeClient)
    client = auth_module._jwks_client()
    assert isinstance(client, FakeClient)
    assert auth_module._jwks_client() is client
    assert created


def test_endpoints_reject_present_but_invalid_token(monkeypatch):
    def _reject(_token: str) -> str:
        raise ValueError("Invalid access token")

    monkeypatch.setattr("app.services.auth.verify_token", _reject)
    with TestClient(app) as client:
        response = client.get("/plans", headers={"Authorization": "Bearer expired-token"})

    assert response.status_code == 401
