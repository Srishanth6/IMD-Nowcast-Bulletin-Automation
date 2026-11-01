"""Download the latest Hyderabad Doppler radar MAX(Z) image from IMD."""
from __future__ import annotations

import io
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from PIL import Image, ImageFile

MAX_Z_PATTERNS = ("max (z)", "max(z)", "max z", "max_z", "max-z", "maxz")
IMAGE_HEADERS = (b"GIF87a", b"GIF89a", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")


class RadarError(RuntimeError):
    pass


def find_max_z_url(page_html: str, base_url: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")
    images = [img for img in soup.find_all("img") if img.get("src")]

    def own_text(img):
        return " ".join([img.get("alt") or "", img.get("title") or "",
                         " ".join(img.get("class") or []), img["src"]]).lower()

    def context_text(img):
        parent = img.parent
        if parent is None or parent.name in ("body", "html", "[document]"):
            return ""
        return parent.get_text(" ", strip=True).lower()

    # Prefer the image's own attributes, then its immediate caption/container.
    for text_of in (own_text, context_text):
        for img in images:
            if any(p in text_of(img) for p in MAX_Z_PATTERNS):
                return urljoin(base_url, img["src"])
    raise RadarError("MAX(Z) radar image not found on the IMD radar page")


def to_png(data: bytes) -> bytes:
    if not data or len(data) < 64 or not data.startswith(IMAGE_HEADERS):
        raise RadarError("radar download is not a valid image")
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if min(image.size) < 8:
            raise RadarError("radar image is too small")
        mode = "RGBA" if image.mode in ("P", "RGBA", "LA") else "RGB"
        out = io.BytesIO()
        image.convert(mode).save(out, format="PNG")
    return out.getvalue()


def download_radar(session, cfg, get) -> bytes:
    kw = dict(retries=cfg.retries, backoff=cfg.retry_backoff_seconds, timeout=cfg.request_timeout)
    page = get(session, cfg.radar_page_url, label="radar page", **kw).text
    url = find_max_z_url(page, cfg.radar_page_url)
    image = get(session, url, label="radar image",
                headers={"Referer": cfg.radar_page_url, "Accept": "image/*"}, **kw)
    return to_png(image.content)
