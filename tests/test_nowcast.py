import pytest

from imd_nowcast import nowcast
from tests import fixtures as fx


def test_parse_times_uses_imd_issue_time():
    issued, valid = nowcast.parse_times(fx.NOWCAST_PAGE)
    assert issued.strftime("%Y-%m-%d %H:%M:%S") == "2026-09-23 20:36:31"
    assert valid.strftime("%H:%M:%S") == "23:36:31"


def test_valid_time_rolls_over_midnight():
    page = fx.NOWCAST_PAGE.replace("20:36:31", "22:30:00").replace("23:36:31", "01:30:00")
    issued, valid = nowcast.parse_times(page)
    assert (valid - issued).total_seconds() == 3 * 3600


def test_missing_times_raise():
    with pytest.raises(nowcast.NowcastParseError):
        nowcast.parse_times("<html></html>")


def test_extract_svg_and_href():
    assert nowcast.extract_svg(fx.NOWCAST_PAGE).startswith('<svg id="svgMap1"')
    assert nowcast.bulletin_href(fx.NOWCAST_PAGE) == "dist_nowcast3.php"


def test_official_docx_warnings_parsed():
    result = nowcast.build_nowcast(fx.NOWCAST_PAGE, fx.official_docx())
    assert result.warnings["orange"].english == fx.ORANGE_EN
    assert result.warnings["orange"].telugu == fx.ORANGE_TE
    assert result.warnings["yellow"].english == fx.YELLOW_EN
    assert "red" not in result.warnings


def test_no_warnings_notice():
    html = "<p>Orange Warning(Be Prepared)</p><p>No warnings / హెచ్చరికలు లేవు</p>"
    result = nowcast.build_nowcast(fx.NOWCAST_PAGE, None, html)
    assert result.no_warnings_english == "No warnings"
    assert result.no_warnings_telugu == "హెచ్చరికలు లేవు"
