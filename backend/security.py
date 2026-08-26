from __future__ import annotations

import time
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("security")

_blocked_extensions = {
    ".py", ".pyc", ".pyo", ".env", ".json", ".log", ".txt",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".bak", ".sql",
    ".db", ".sqlite", ".key", ".pem", ".crt",
}

_blocked_directories = {
    "__pycache__", ".git", ".env", "node_modules", ".idea", ".vscode",
    "data",
}


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        self._attempts[key] = [t for t in self._attempts[key] if now - t < self.window]
        if len(self._attempts[key]) >= self.max_requests:
            return True
        self._attempts[key].append(now)
        return False

    def reset(self, key: str):
        self._attempts.pop(key, None)

    def get_retry_after(self, key: str) -> int:
        attempts = self._attempts.get(key, [])
        if not attempts:
            return 0
        now = time.time()
        valid = [t for t in attempts if now - t < self.window]
        if not valid:
            return 0
        oldest_in_window = min(valid)
        return int(self.window - (now - oldest_in_window)) + 1


login_limiter = RateLimiter(max_requests=15, window_seconds=60)


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"

    ct = response.headers.get("content-type", "")
    if "text/html" in ct:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )

    return response


async def block_sensitive_files_middleware(request: Request, call_next):
    path = request.url.path.lower()

    ext = ""
    dot_pos = path.rfind(".")
    if dot_pos > 0:
        ext = path[dot_pos:]

    if ext in _blocked_extensions:
        return JSONResponse(status_code=403, content={"error": "Access denied"})

    for blocked_dir in _blocked_directories:
        if f"/{blocked_dir}" in path or path.startswith(blocked_dir):
            return JSONResponse(status_code=403, content={"error": "Access denied"})

    return await call_next(request)


async def login_rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/auth/login" and request.method == "POST":
        client_ip = get_client_ip(request)
        if login_limiter.is_rate_limited(client_ip):
            retry = login_limiter.get_retry_after(client_ip)
            log.warning("Rate limited login attempt from %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={"error": f"Too many attempts. Try again in {retry}s."},
                headers={"Retry-After": str(retry)},
            )

    return await call_next(request)
