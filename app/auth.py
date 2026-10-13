"""Defence in depth behind Cloudflare Access: reject requests that didn't come through Access."""

import jwt
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import PlainTextResponse

EXEMPT_PATHS = {"/healthz"}


class AccessVerifier:
    def __init__(self, team_domain: str, audience: str, jwks_client=None):
        self.issuer = f"https://{team_domain}"
        self.audience = audience
        self.jwks_client = jwks_client or jwt.PyJWKClient(
            f"{self.issuer}/cdn-cgi/access/certs", cache_keys=True, lifespan=3600
        )

    def verify(self, token: str) -> dict:
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token, signing_key.key, algorithms=["RS256"], audience=self.audience, issuer=self.issuer
        )


def install_access_check(app: FastAPI, verifier: AccessVerifier) -> None:
    @app.middleware("http")
    async def access_check(request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        token = request.headers.get("cf-access-jwt-assertion") or request.cookies.get("CF_Authorization")
        if not token:
            return PlainTextResponse("Forbidden", status_code=403)
        try:
            await run_in_threadpool(verifier.verify, token)
        except jwt.PyJWTError:
            return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)
