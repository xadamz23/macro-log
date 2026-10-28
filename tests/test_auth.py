import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import AccessVerifier, TailnetProxy
from app.db import Base
from app.main import create_app

TEAM = "myteam.cloudflareaccess.com"
AUD = "test-aud"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJWKS:
    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=KEY.public_key())


def _token(**overrides):
    claims = {"aud": AUD, "iss": f"https://{TEAM}", "exp": int(time.time()) + 60, "email": "me@example.com"}
    claims.update(overrides)
    return jwt.encode(claims, KEY, algorithm="RS256")


@pytest.fixture
def secured(settings):
    application = create_app(settings, access_verifier=AccessVerifier(TEAM, AUD, jwks_client=FakeJWKS()))
    Base.metadata.create_all(application.state.engine)
    with TestClient(application) as c:
        yield c
    application.state.engine.dispose()


def test_missing_token_forbidden(secured):
    assert secured.get("/").status_code == 403


def test_healthz_exempt(secured):
    assert secured.get("/healthz").status_code == 200


def test_valid_header_allowed(secured):
    assert secured.get("/settings", headers={"Cf-Access-Jwt-Assertion": _token()}).status_code == 200


def test_valid_cookie_allowed(secured):
    secured.cookies.set("CF_Authorization", _token())
    assert secured.get("/settings").status_code == 200


@pytest.mark.parametrize("overrides", [{"aud": "other"}, {"iss": "https://evil.example"}, {"exp": int(time.time()) - 10}])
def test_bad_claims_forbidden(secured, overrides):
    assert secured.get("/", headers={"Cf-Access-Jwt-Assertion": _token(**overrides)}).status_code == 403


def test_garbage_token_forbidden(secured):
    assert secured.get("/", headers={"Cf-Access-Jwt-Assertion": "not-a-jwt"}).status_code == 403


# TestClient connects from the peer "testclient". The fake resolver decides whether that peer is the Tailscale sidecar.
PROXY = "macrolog-ts"
TAILNET_USER = {"Tailscale-User-Login": "me@example.com"}


def _behind_tailnet_proxy(settings, proxy_ips):
    proxy = TailnetProxy(PROXY, resolve=lambda host: (host, [], proxy_ips if host == PROXY else []))
    application = create_app(settings, access_verifier=AccessVerifier(TEAM, AUD, jwks_client=FakeJWKS()), tailnet_proxy=proxy)
    Base.metadata.create_all(application.state.engine)

    @application.get("/_client")
    def _client(request: Request) -> dict:
        return {"host": request.client.host, "scheme": request.url.scheme}

    return application


@pytest.fixture
def from_proxy(settings):
    application = _behind_tailnet_proxy(settings, ["testclient"])
    with TestClient(application) as c:
        yield c
    application.state.engine.dispose()


@pytest.fixture
def from_elsewhere(settings):
    application = _behind_tailnet_proxy(settings, ["172.21.0.10"])
    with TestClient(application) as c:
        yield c
    application.state.engine.dispose()


def test_tailnet_user_via_proxy_allowed(from_proxy):
    assert from_proxy.get("/settings", headers=TAILNET_USER).status_code == 200


def test_proxy_without_tailnet_user_forbidden(from_proxy):
    assert from_proxy.get("/settings").status_code == 403


def test_tailnet_header_from_other_peer_forbidden(from_elsewhere):
    assert from_elsewhere.get("/settings", headers=TAILNET_USER).status_code == 403


def test_forwarded_for_cannot_impersonate_proxy(from_elsewhere):
    headers = TAILNET_USER | {"X-Forwarded-For": "172.21.0.10"}
    assert from_elsewhere.get("/settings", headers=headers).status_code == 403


def test_access_token_still_allowed_with_proxy_configured(from_elsewhere):
    assert from_elsewhere.get("/settings", headers={"Cf-Access-Jwt-Assertion": _token()}).status_code == 200


def test_forwarded_headers_still_applied(from_proxy):
    headers = TAILNET_USER | {"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https"}
    assert from_proxy.get("/_client", headers=headers).json() == {"host": "203.0.113.7", "scheme": "https"}


def test_unresolvable_proxy_forbidden(settings):
    def resolve(host):
        raise OSError("no such host")

    proxy = TailnetProxy(PROXY, resolve=resolve)
    application = create_app(settings, access_verifier=AccessVerifier(TEAM, AUD, jwks_client=FakeJWKS()), tailnet_proxy=proxy)
    Base.metadata.create_all(application.state.engine)
    with TestClient(application) as c:
        assert c.get("/settings", headers=TAILNET_USER).status_code == 403
    application.state.engine.dispose()


def test_proxy_name_shared_by_another_container_forbidden(settings):
    application = _behind_tailnet_proxy(settings, ["testclient", "172.21.0.99"])
    with TestClient(application) as c:
        assert c.get("/settings", headers=TAILNET_USER).status_code == 403
    application.state.engine.dispose()


def test_proxy_lookup_is_cached_briefly():
    calls = []
    now = [0.0]
    proxy = TailnetProxy(PROXY, resolve=lambda host: calls.append(host) or (host, [], ["10.0.0.5"]), clock=lambda: now[0])
    assert proxy.is_proxy("10.0.0.5") and proxy.is_proxy("10.0.0.5")
    assert len(calls) == 1
    now[0] += 60
    assert proxy.is_proxy("10.0.0.5")
    assert len(calls) == 2


def test_settings_enable_tailnet_proxy(settings, monkeypatch):
    monkeypatch.setattr("app.auth.socket.gethostbyname_ex", lambda host: (host, [], ["testclient"] if host == PROXY else []))
    settings.tailnet_proxy_host = PROXY
    application = create_app(settings, access_verifier=AccessVerifier(TEAM, AUD, jwks_client=FakeJWKS()))
    Base.metadata.create_all(application.state.engine)
    with TestClient(application) as c:
        assert c.get("/settings", headers=TAILNET_USER).status_code == 200
    application.state.engine.dispose()
