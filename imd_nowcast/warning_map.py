"""Render the Telangana district warning map (SVG) to PNG."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


class MapRenderError(RuntimeError):
    pass


def find_browser(configured: str = "") -> str:
    for candidate in (configured, shutil.which("chrome"), shutil.which("google-chrome"),
                      shutil.which("chromium"), *CHROME_CANDIDATES):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise MapRenderError("Chrome/Edge not found; set chrome_path in config.local.json")


def render_svg_to_png(svg: str, png_path: Path, chrome_path: str = "") -> Path:
    """Screenshot the 650x750 SVG with headless Chrome/Edge."""
    png_path = Path(png_path)
    with tempfile.TemporaryDirectory(prefix="imd-map-") as tmp:
        html_path = Path(tmp) / "map.html"
        html_path.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;width:650px;height:750px;overflow:hidden;background:#fff}"
            f"</style></head><body>{svg}</body></html>", encoding="utf-8")
        shot = Path(tmp) / "map.png"
        subprocess.run([
            find_browser(chrome_path), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-first-run", "--window-size=650,750",
            f"--user-data-dir={Path(tmp) / 'profile'}", f"--screenshot={shot}",
            html_path.resolve().as_uri(),
        ], check=True, timeout=90, capture_output=True)
        if not shot.is_file():
            raise MapRenderError("browser did not write the warning-map PNG")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shot, png_path)
    return png_path
