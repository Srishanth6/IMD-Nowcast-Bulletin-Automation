"""HTTP helpers with retries and address redaction for logs."""
from __future__ import annotations

import logging
import re
import time

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_URL_RE = re.compile(r"[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
_HOST_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b|host='[^']*'|port=\d+")


def redact(text: object) -> str:
    """Remove URLs, IP addresses and ports so logs never leak the server address."""
    return _HOST_RE.sub("<redacted>", _URL_RE.sub("<url>", str(text)))


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {"User-Agent": USER_AGENT, "Cache-Control": "no-cache", "Pragma": "no-cache"}
    )
    return session


def get_with_retries(session, url, *, label, retries=3, backoff=5.0, timeout=30, **kwargs):
    """GET ``url`` with exponential backoff. Raises the last error on failure."""
    last_error: Exception | None = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = session.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            log.warning("%s: attempt %d/%d failed: %s", label, attempt, retries, redact(error))
            if attempt < retries:
                time.sleep(backoff * (2 ** (attempt - 1)))
    raise RuntimeError(f"{label} failed after {retries} attempts: {redact(last_error)}")
