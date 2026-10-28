"""Defence in depth behind Cloudflare Access: reject requests that didn't come through Access.

Requests through this app's Tailscale sidecar are allowed too. `tailscale serve` sets Tailscale-User-Login for tailnet
users and strips any copy the client sent, but any container on the Docker network could forge the header, so it only
counts when the TCP peer really is the sidecar.
"""

import socket
import time

import jwt
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import PlainTextResponse

EXEMPT_PATHS = {"/healthz"}
TAILNET_USER_HEADER = "tailscale-user-login"


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


class TailnetProxy:
    """The Tailscale sidecar's container name. Its IP can change on restart, so lookups are only cached briefly."""

    def __init__(self, host: str, resolve=None, clock=time.monotonic, ttl: float = 5.0):
        self.host = host
        self.resolve = resolve
        self.clock = clock
        self.ttl = ttl
        self._ips: frozenset[str] = frozenset()
        self._expires = float("-inf")

    def is_proxy(self, ip: str) -> bool:
        now = self.clock()
        if now >= self._expires:
            resolve = self.resolve or socket.gethostbyname_ex
            try:
                ips = frozenset(resolve(self.host)[2])
            except OSError:
                ips = frozenset()
            # More than one address means another container shares the name (a Docker network alias); trust neither.
            self._ips = ips if len(ips) == 1 else frozenset()
            self._expires = now + self.ttl
        return ip in self._ips


class RecordPeer:
    """Outermost middleware: keep the TCP peer before ProxyHeadersMiddleware swaps scope["client"] for X-Forwarded-For."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope["peer"] = scope.get("client")
        await self.app(scope, receive, send)


def install_access_check(app: FastAPI, verifier: AccessVerifier, tailnet_proxy: TailnetProxy | None = None) -> None:
    @app.middleware("http")
    async def access_check(request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        peer = request.scope.get("peer")
        if tailnet_proxy is not None and peer and request.headers.get(TAILNET_USER_HEADER):
            if await run_in_threadpool(tailnet_proxy.is_proxy, peer[0]):
                return await call_next(request)
        token = request.headers.get("cf-access-jwt-assertion") or request.cookies.get("CF_Authorization")
        if not token:
            return PlainTextResponse("Forbidden", status_code=403)
        try:
            await run_in_threadpool(verifier.verify, token)
        except jwt.PyJWTError:
            return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)
