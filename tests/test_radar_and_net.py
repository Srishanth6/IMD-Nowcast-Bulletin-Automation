from unittest import mock

import pytest
import requests

from imd_nowcast import net, radar
from tests import fixtures as fx


def test_find_max_z_url():
    url = radar.find_max_z_url(fx.RADAR_PAGE, "https://mausam.imd.gov.in/hyderabad/index_radar.php")
    assert url == "https://mausam.imd.gov.in/Radar/caz_hyd.gif"


def test_find_max_z_missing():
    with pytest.raises(radar.RadarError):
        radar.find_max_z_url("<img src='a.png'>", "https://x/")


def test_to_png_converts_gif():
    assert radar.to_png(fx.image_bytes("GIF")).startswith(b"\x89PNG")


def test_to_png_rejects_html():
    with pytest.raises(radar.RadarError):
        radar.to_png(b"<html>error page</html>" * 10)


def test_redact_hides_address():
    text = "HTTPConnectionPool(host='192.0.2.10', port=9999): http://192.0.2.10:9999/x failed"
    out = net.redact(text)
    assert "192.0.2.10" not in out and "9999" not in out


def test_retries_then_succeeds():
    ok = mock.Mock(status_code=200)
    session = mock.Mock()
    session.get.side_effect = [requests.ConnectionError("down"), ok]
    with mock.patch("time.sleep"):
        assert net.get_with_retries(session, "http://h/", label="t", retries=3, backoff=0) is ok
    assert session.get.call_count == 2


def test_retries_exhausted():
    session = mock.Mock()
    session.get.side_effect = requests.ConnectionError("host='192.0.2.20' unreachable")
    with mock.patch("time.sleep"), pytest.raises(RuntimeError) as err:
        net.get_with_retries(session, "http://h/", label="nowcast page", retries=2, backoff=0)
    assert "192.0.2.20" not in str(err.value)
