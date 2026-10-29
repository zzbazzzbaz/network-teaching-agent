from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from app.gateway.http_client import (
    UpstreamAuthError,
    UpstreamContractError,
    UpstreamStatusError,
    UpstreamUnavailable,
    build_http_client,
    request_json,
)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url="http://agent.test",
        transport=httpx.MockTransport(handler),
    )


def test_build_http_client_sets_base_url_timeout_headers_and_trust_env() -> None:
    client = build_http_client(
        base_url="http://agent.test/",
        timeout_seconds=5,
        headers={"X-Internal-Token": "secret"},
    )
    try:
        assert client.base_url == httpx.URL("http://agent.test")
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 5.0
        assert client.trust_env is False
        assert client.headers["X-Internal-Token"] == "secret"
    finally:
        client.close()


def test_request_json_returns_none_for_204() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    assert request_json(_client(handler), method="DELETE", path="/threads/1") is None


def test_request_json_returns_parsed_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/store/items/search"
        assert request.url.params["limit"] == "1"
        assert json.loads(request.content) == {"offset": 0}
        return httpx.Response(200, json={"items": []})

    result = request_json(
        _client(handler),
        method="POST",
        path="/store/items/search",
        params={"limit": 1},
        json={"offset": 0},
    )
    assert result == {"items": []}


def test_request_json_merges_default_and_per_request_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Internal-Token"] == "secret"
        assert request.headers["X-Test"] == "override"
        return httpx.Response(200, json={})

    client = httpx.Client(
        base_url="http://agent.test",
        headers={"X-Internal-Token": "secret", "X-Test": "default"},
        transport=httpx.MockTransport(handler),
    )
    request_json(
        client,
        method="GET",
        path="/store/items",
        headers={"X-Test": "override"},
    )


def test_request_json_rejects_empty_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    with pytest.raises(UpstreamContractError):
        request_json(_client(handler), method="GET", path="/store/items")


def test_request_json_rejects_non_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    with pytest.raises(UpstreamContractError):
        request_json(_client(handler), method="GET", path="/store/items")


@pytest.mark.parametrize("status_code", [401, 403])
def test_request_json_maps_auth_errors(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    with pytest.raises(UpstreamAuthError):
        request_json(_client(handler), method="GET", path="/store/items")


def test_request_json_maps_5xx_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(UpstreamUnavailable):
        request_json(_client(handler), method="GET", path="/store/items")


def test_request_json_maps_other_4xx_to_status_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, text="conflict")

    with pytest.raises(UpstreamStatusError) as error:
        request_json(_client(handler), method="GET", path="/store/items")
    assert error.value.status_code == 409


@pytest.mark.parametrize(
    "exception",
    [
        httpx.ReadTimeout("timeout"),
        httpx.ConnectError("connect failed"),
    ],
)
def test_request_json_maps_transport_errors_to_unavailable(
    exception: httpx.HTTPError,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    with pytest.raises(UpstreamUnavailable):
        request_json(_client(handler), method="GET", path="/store/items")
