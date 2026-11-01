"""Build the District level Nowcast of Telangana Word bulletin."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt
from PIL import Image

from .config import ROOT
from .nowcast import Nowcast, Warning

ASSETS = ROOT / "assets"
HEADER = ASSETS / "imd_header.jpg"
IMPACT_PAGES = (
    ASSETS / "expected_impacts_moderate.jpg",
    ASSETS / "expected_impacts_heavy_rain.jpg",
    ASSETS / "expected_impacts_very_severe.jpg",
)
LEVEL_STYLE = {
    "red": ("Red Warning(Take Action)", "FF0000"),
    "orange": ("Orange Warning(Be Prepared)", "FFA500"),
    "yellow": ("Yellow Warning(Be Updated)", "FFFF00"),
}
ALWAYS_SHOWN = ("orange", "yellow")
DUTY_OFFICER = "డ్యూటీ అధికారి / ड्यूटी अधिकारी / Duty Officer"


def issue_line(issued: datetime) -> str:
    return f"TIME OF ISSUE: {issued:%Y-%m-%d} ({issued:%H:%M:%S} Hrs IST)"


def valid_line(valid: datetime) -> str:
    return f"Valid upto: ({valid:%H:%M:%S} Hrs IST)"


def _font(run, name="Times New Roman", size=11, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:cs"), name)


def _shade(run, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    run._element.get_or_add_rPr().append(shd)


def _para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, after=4):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    return p


def _fit(path: Path, max_w: float, max_h: float):
    with Image.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Inches(w * scale), Inches(h * scale)


def _picture(paragraph, path: Path, max_w: float, max_h: float):
    w, h = _fit(path, max_w, max_h)
    paragraph.add_run().add_picture(str(path), width=w, height=h)


def resolve_sections(nowcast: Nowcast) -> dict[str, Warning]:
    """Orange and Yellow are always shown (with the IMD no-warning notice if empty)."""
    out = {}
    for level in LEVEL_STYLE:
        item = nowcast.warnings.get(level) or Warning()
        if not (item.english or item.telugu) and level in ALWAYS_SHOWN:
            item = Warning(nowcast.no_warnings_english, nowcast.no_warnings_telugu)
        if item.english or item.telugu or level in ALWAYS_SHOWN:
            out[level] = item
    return out


def build_bulletin(nowcast: Nowcast, radar_png: Path, map_png: Path, out_path: Path) -> Path:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, side, Cm(1.27))

    if HEADER.is_file():
        _picture(_para(doc, WD_ALIGN_PARAGRAPH.CENTER, 0), HEADER, 6.25, 1.36)

    _font(_para(doc, WD_ALIGN_PARAGRAPH.CENTER).add_run("District level Nowcast of Telangana"),
          size=16, bold=True)

    times = doc.add_table(rows=1, cols=2)
    times.alignment = WD_TABLE_ALIGNMENT.CENTER
    left, right = times.rows[0].cells
    _font(left.paragraphs[0].add_run(issue_line(nowcast.issued)), bold=True)
    right.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _font(right.paragraphs[0].add_run(valid_line(nowcast.valid)), bold=True)

    for level, item in resolve_sections(nowcast).items():
        title, fill = LEVEL_STYLE[level]
        run = _para(doc, after=2).add_run(title)
        _font(run, size=12, bold=True)
        _shade(run, fill)
        if item.english:
            _font(_para(doc, after=2).add_run(item.english))
        if item.telugu:
            _font(_para(doc, after=6).add_run(item.telugu), name="Nirmala UI")

    images = doc.add_table(rows=1, cols=2)
    images.alignment = WD_TABLE_ALIGNMENT.CENTER
    radar_cell, map_cell = images.rows[0].cells
    _picture(radar_cell.paragraphs[0], Path(radar_png), 3.47, 2.84)
    _picture(map_cell.paragraphs[0], Path(map_png), 3.47, 4.01)

    _font(_para(doc, WD_ALIGN_PARAGRAPH.RIGHT).add_run(DUTY_OFFICER), name="Nirmala UI", size=12)

    for page in IMPACT_PAGES:
        if page.is_file():
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            _picture(_para(doc, WD_ALIGN_PARAGRAPH.CENTER), page, 6.25, 9.4)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path
