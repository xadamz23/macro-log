"""Content-hash cache busting for files under app/static."""

import hashlib
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

STATIC_DIR = Path(__file__).parent / "static"
IMMUTABLE = "public, max-age=31536000, immutable"


class AssetHasher:
    """Short sha256 digests of static files, recomputed when a file's mtime or size changes."""

    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[str, tuple[tuple[int, int], str]] = {}

    def digest(self, path: str) -> str:
        stat = (self.root / path).stat()
        key = (stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(path)
        if cached and cached[0] == key:
            return cached[1]
        with open(self.root / path, "rb") as f:
            value = hashlib.file_digest(f, "sha256").hexdigest()[:10]
        self._cache[path] = (key, value)
        return value

    def url(self, path: str) -> str:
        return f"/static/{path}?v={self.digest(path)}"

    def version(self) -> str:
        """One digest over every static file; changes when any of them does."""
        combined = hashlib.sha256()
        for file in sorted(p for p in self.root.rglob("*") if p.is_file()):
            rel = file.relative_to(self.root).as_posix()
            combined.update(f"{rel}:{self.digest(rel)}\n".encode())
        return combined.hexdigest()[:10]


assets = AssetHasher(STATIC_DIR)


class CachedStaticFiles(StaticFiles):
    """Versioned URLs (?v=<current digest>) are cached forever; anything else must revalidate."""

    def file_response(self, full_path, stat_result, scope, status_code: int = 200) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        rel = Path(full_path).resolve().relative_to(STATIC_DIR.resolve()).as_posix()
        query = scope.get("query_string", b"").decode()
        params = dict(part.split("=", 1) for part in query.split("&") if "=" in part)
        current = params.get("v") == assets.digest(rel)
        response.headers["cache-control"] = IMMUTABLE if current else "no-cache"
        return response
