import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import AccessVerifier
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
