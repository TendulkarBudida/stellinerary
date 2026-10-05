from datetime import datetime, timezone

import pytest
from httpx import HTTPStatusError, Request, Response

from app.config import Settings
from app.services import llm_client, weather_client


def test_settings_load_runtime_and_llm_values_from_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ENV=production\nLOG_LEVEL=WARNING\n"
        "LLM_BASE_URL=https://example.test/v1\n"
        "LLM_API_KEY=test-key\nLLM_MODEL=test-model\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.env == "production"
    assert settings.log_level == "WARNING"
    assert settings.llm_base_url == "https://example.test/v1"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "test-model"


def test_settings_have_safe_defaults_without_env_file(tmp_path):
    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.env == "development"
    assert settings.log_level == "INFO"
    assert settings.llm_api_key == ""
    assert settings.llm_base_url.startswith("https://")
    assert settings.llm_model


def test_llm_client_uses_configured_endpoint_and_key(monkeypatch):
    created = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setattr(llm_client, "AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(llm_client.settings, "llm_base_url", "https://llm.test/v1")
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "secret")

    llm_client.get_llm_client()

    assert created == {"base_url": "https://llm.test/v1", "api_key": "secret"}


@pytest.mark.asyncio
async def test_chat_completion_returns_mocked_provider_text(monkeypatch):
    class FakeCompletions:
        async def create(self, **kwargs):
            assert kwargs["model"] == "test-model"
            assert kwargs["temperature"] == 0.2
            return type("Response", (), {
                "choices": [type("Choice", (), {
                    "message": type("Message", (), {"content": "offline response"})()
                })()]
            })()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm_client, "get_llm_client", lambda: FakeClient())
    monkeypatch.setattr(llm_client.settings, "llm_model", "test-model")

    result = await llm_client.chat_completion([{"role": "user", "content": "hello"}], temperature=0.2)

    assert result == "offline response"


@pytest.mark.asyncio
async def test_weather_client_builds_request_and_parses_response(monkeypatch):
    weather_client.clear_cache()
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"dataseries": [{"timepoint": 0, "cloudcover": 1}]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]
            captured["follow_redirects"] = kwargs["follow_redirects"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(weather_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await weather_client.fetch_astro_weather(13.37123, 77.68123)

    assert result == {"dataseries": [{"timepoint": 0, "cloudcover": 1}]}
    assert captured["follow_redirects"] is True
    assert captured["url"] == weather_client.SEVEN_TIMER_BASE
    assert captured["params"] == {
        "product": "astro",
        "lat": 13.37,
        "lon": 77.68,
        "output": "json",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [TimeoutError("timeout"), ValueError("bad response")])
async def test_weather_client_returns_none_for_transport_failures(monkeypatch, error):
    weather_client.clear_cache()

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            raise error

    monkeypatch.setattr(weather_client.httpx, "AsyncClient", FakeAsyncClient)

    assert await weather_client.fetch_astro_weather(13.37, 77.68) is None


@pytest.mark.asyncio
async def test_weather_client_returns_none_for_http_errors(monkeypatch):
    weather_client.clear_cache()

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            request = Request("GET", url)
            raise HTTPStatusError("server error", request=request, response=Response(503, request=request))

    monkeypatch.setattr(weather_client.httpx, "AsyncClient", FakeAsyncClient)

    assert await weather_client.fetch_astro_weather(13.37, 77.68) is None