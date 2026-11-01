"""Configuration loading.

The IMD nowcast server address is private and must never be committed.
It is read from ``config.local.json`` (git-ignored) or from the
``IMD_NOWCAST_URL`` environment variable.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG = ROOT / "config.local.json"
DEFAULT_RADAR_URL = "https://mausam.imd.gov.in/hyderabad/index_radar.php?id=Hyderabad"


class ConfigError(RuntimeError):
    pass


@dataclass
class Config:
    nowcast_page_url: str
    radar_page_url: str = DEFAULT_RADAR_URL
    output_dir: Path = field(default_factory=lambda: ROOT / "output")
    log_dir: Path = field(default_factory=lambda: ROOT / "logs")
    request_timeout: int = 30
    retries: int = 3
    retry_backoff_seconds: float = 5
    chrome_path: str = ""


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


def load_config(path: Path | None = None) -> Config:
    _load_env_file(ROOT / ".env")
    data: dict = {}
    path = Path(path) if path else LOCAL_CONFIG
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    url = os.environ.get("IMD_NOWCAST_URL") or data.get("nowcast_page_url", "")
    if not url or "<" in url:
        raise ConfigError(
            "IMD nowcast URL is not configured. Copy config.example.json to "
            "config.local.json and fill in nowcast_page_url, or set IMD_NOWCAST_URL."
        )

    def _path(key: str, default: str) -> Path:
        value = Path(data.get(key) or default)
        return value if value.is_absolute() else ROOT / value

    return Config(
        nowcast_page_url=url,
        radar_page_url=os.environ.get("IMD_RADAR_URL") or data.get("radar_page_url") or DEFAULT_RADAR_URL,
        output_dir=_path("output_dir", "output"),
        log_dir=_path("log_dir", "logs"),
        request_timeout=int(data.get("request_timeout", 30)),
        retries=int(data.get("retries", 3)),
        retry_backoff_seconds=float(data.get("retry_backoff_seconds", 5)),
        chrome_path=data.get("chrome_path", ""),
    )
