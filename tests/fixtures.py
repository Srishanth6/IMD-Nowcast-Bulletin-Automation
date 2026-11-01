"""Synthetic IMD responses used by the tests (no real server address)."""
import io

from docx import Document
from PIL import Image

SVG = ('<svg id="svgMap1" width="650" height="750" xmlns="http://www.w3.org/2000/svg">'
       '<path d="M0 0 L10 0 L10 10 Z" fill="orange"/><path d="M0 0 L5 5 Z" fill="yellow"/></svg>')

NOWCAST_PAGE = (
    "Date (DB): 2026-09-23<br>Time TOI (DB): 20:36:31<br>Valid Up To (DB): 23:36:31<br>"
    "<!DOCTYPE html><html><body>"
    "<a href='dist_nowcast3.php'>Download Nowcast Bulletin</a>"
    f"{SVG}</body></html>"
)

ORANGE_EN = ("Moderate rain likely in HANAMKONDA, J. BHUPALPALLY, JAGTIAL, KARIMNAGAR, "
             "MAHABUBNAGAR, NAGARKURNOOL, PEDDAPALLE, WARANGAL districts.")
ORANGE_TE = "హన్మకొండ, వరంగల్ జిల్లాల్లో మోస్తరు వర్షం వచ్చే అవకాశం వుంది."
YELLOW_EN = "Light rain: < 5 mm/hr likely in ADILABAD, KHAMMAM, NALGONDA districts."
YELLOW_TE = "ఆదిలాబాద్, ఖమ్మం, నల్గొండ జిల్లాల్లో తేలికపాటి వర్షం వచ్చే అవకాశం వుంది."


def official_docx() -> bytes:
    doc = Document()
    for text in ("District level Nowcast of Telangana",
                 "TIME OF ISSUE: 2026-09-23 (20:36:31 Hrs IST)",
                 "Orange Warning(Be Prepared)", ORANGE_EN, ORANGE_TE,
                 "Yellow Warning(Be Updated)", YELLOW_EN, YELLOW_TE,
                 "డ్యూటీ అధికారి / ड्यूटी अधिकारी / Duty Officer"):
        doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


RADAR_PAGE = ('<html><body><img src="/img/logo.png" alt="IMD">'
              '<div>MAX (Z)<img src="/Radar/caz_hyd.gif"></div></body></html>')


def image_bytes(fmt="GIF", size=(120, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (30, 120, 30)).save(buf, format=fmt)
    return buf.getvalue()
