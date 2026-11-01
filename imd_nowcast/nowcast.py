"""Fetch and parse the IMD Telangana district nowcast page and its bulletin."""
from __future__ import annotations

import html as html_lib
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

IST = timezone(timedelta(hours=5, minutes=30))
NOWCAST_VALIDITY = timedelta(hours=3)
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LEVELS = ("red", "orange", "yellow")


class NowcastParseError(RuntimeError):
    pass


@dataclass
class Warning:
    english: str = ""
    telugu: str = ""


@dataclass
class Nowcast:
    issued: datetime
    valid: datetime
    warnings: dict[str, Warning] = field(default_factory=dict)
    no_warnings_english: str = ""
    no_warnings_telugu: str = ""
    map_svg: str = ""
    bulletin_href: str | None = None


def has_telugu(text: str) -> bool:
    return bool(re.search(r"[\u0C00-\u0C7F]", text))


def extract_svg(page_html: str) -> str:
    """Return the Telangana district warning map (<svg id="svgMap1">)."""
    match = re.search(
        r"<svg\b(?=[^>]*\bid\s*=\s*['\"]svgMap1['\"])[^>]*>.*?</svg>",
        page_html, flags=re.I | re.S,
    ) or re.search(
        # IMD sometimes emits the map with a blank id after PHP warnings.
        r"<svg\b[^>]*width=['\"]650['\"][^>]*height=['\"]750['\"][^>]*>.*?</svg>",
        page_html, flags=re.I | re.S,
    )
    if not match:
        raise NowcastParseError("Telangana warning map (svgMap1) not found on nowcast page")
    return match.group(0).replace("\x00", "")


def parse_times(page_html: str) -> tuple[datetime, datetime]:
    """Issue/valid time as published by IMD (never the local clock)."""
    date = re.search(r"Date \(DB\):\s*(\d{4}-\d{2}-\d{2})", page_html)
    toi = re.search(r"Time TOI \(DB\):\s*(\d{1,2}:\d{2}:\d{2})", page_html)
    upto = re.search(r"Valid Up To \(DB\):\s*(\d{1,2}:\d{2}:\d{2})", page_html)
    if not (date and toi):
        raise NowcastParseError("nowcast page has no Date (DB) / Time TOI (DB)")
    issued = datetime.strptime(f"{date[1]} {toi[1]}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    if upto:
        valid = datetime.strptime(f"{date[1]} {upto[1]}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        if valid <= issued:
            valid += timedelta(days=1)
    else:
        valid = issued + NOWCAST_VALIDITY
    return issued, valid


def _heading_level(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text).lower()
    for level in LEVELS:
        if compact.startswith(f"{level}warning"):
            return level
    return None


def _is_structural(text: str) -> bool:
    compact = re.sub(r"\s+", "", text).lower()
    return (
        _heading_level(text) is not None
        or compact.startswith(("timeofissue", "validupto", "districtlevelnowcast", "nowarnings"))
        or "duty officer" in text.lower()
        or "డ్యూటీ" in text
    )


def parse_blocks(blocks: list[str]) -> dict:
    """Turn bulletin paragraphs into {level: Warning} plus a no-warnings notice."""
    warnings: dict[str, Warning] = {}
    no_en = no_te = ""
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if re.search(r"no\s*warnings", block, re.I) or "హెచ్చరికలు లేవు" in block:
            for part in re.split(r"\s*/\s*", block):
                if has_telugu(part):
                    no_te = no_te or part.strip()
                elif part.strip():
                    no_en = no_en or part.strip()
            i += 1
            continue
        level = _heading_level(block)
        if level is None:
            i += 1
            continue
        item = Warning()
        j = i + 1
        while j < len(blocks) and not _is_structural(blocks[j]):
            text = blocks[j]
            if has_telugu(text) and not re.search(r"[A-Za-z]{3}", text):
                item.telugu = f"{item.telugu} {text}".strip()
            else:
                item.english = f"{item.english} {text}".strip()
            j += 1
        warnings[level] = item
        i = j
    return {"warnings": warnings, "no_en": no_en, "no_te": no_te}


def docx_paragraphs(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    out = []
    for para in root.iter(f"{W_NS}p"):
        text = "".join(node.text or "" for node in para.iter(f"{W_NS}t"))
        text = html_lib.unescape(re.sub(r"\s+", " ", text)).strip()
        if text:
            out.append(text)
    return out


def html_paragraphs(page: str) -> list[str]:
    page = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", page, flags=re.I | re.S)
    out: list[str] = []
    for match in re.finditer(r"<(h[1-6]|p|td|div|li)(?:\s[^>]*)?>(.*?)</\1>", page, re.I | re.S):
        text = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match[2]))).strip()
        if text and text not in out:
            out.append(text)
    return out


def bulletin_href(page_html: str) -> str | None:
    match = re.search(
        r"<a\s+href=['\"]([^'\"]+)['\"][^>]*>\s*Download Nowcast Bulletin", page_html, re.I
    )
    return match[1] if match else None


def build_nowcast(page_html: str, bulletin_bytes: bytes | None = None,
                  bulletin_html: str | None = None) -> Nowcast:
    issued, valid = parse_times(page_html)
    nowcast = Nowcast(issued=issued, valid=valid, map_svg=extract_svg(page_html),
                      bulletin_href=bulletin_href(page_html))
    sources = []
    if bulletin_bytes:
        sources.append(parse_blocks(docx_paragraphs(bulletin_bytes)))
    if bulletin_html:
        sources.append(parse_blocks(html_paragraphs(bulletin_html)))
    for src in sources:
        for level, item in src["warnings"].items():
            current = nowcast.warnings.setdefault(level, Warning())
            current.english = current.english or item.english
            current.telugu = current.telugu or item.telugu
        nowcast.no_warnings_english = nowcast.no_warnings_english or src["no_en"]
        nowcast.no_warnings_telugu = nowcast.no_warnings_telugu or src["no_te"]
    return nowcast


def fetch_nowcast(session, cfg, get) -> tuple[str, Nowcast]:
    """Download the nowcast page plus IMD's own Word/HTML bulletin text."""
    kw = dict(retries=cfg.retries, backoff=cfg.retry_backoff_seconds, timeout=cfg.request_timeout)
    page = get(session, cfg.nowcast_page_url, label="nowcast page",
               params={"_": str(int(datetime.now(IST).timestamp()))}, **kw).text
    href = bulletin_href(page) or "dist_nowcast3.php"
    docx_bytes = html_text = None
    try:
        docx_bytes = get(session, urljoin(cfg.nowcast_page_url, href), label="official bulletin", **kw).content
    except RuntimeError:
        pass
    try:
        html_text = get(session, urljoin(cfg.nowcast_page_url, "dist_nowcast4.php"),
                        label="HTML bulletin", **kw).content.decode("utf-8", "replace")
    except RuntimeError:
        pass
    try:
        nowcast = build_nowcast(page, docx_bytes, html_text)
    except zipfile.BadZipFile:
        nowcast = build_nowcast(page, None, html_text)
    return page, nowcast
