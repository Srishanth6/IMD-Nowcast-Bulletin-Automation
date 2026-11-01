import json
from pathlib import Path
from unittest import mock

from docx import Document
from PIL import Image

from imd_nowcast import pipeline
from imd_nowcast.config import Config, ConfigError, load_config
from tests import fixtures as fx


def fake_get(session, url, *, label, **kwargs):
    response = mock.Mock()
    if label == "nowcast page":
        response.text = fx.NOWCAST_PAGE
    elif label == "official bulletin":
        response.content = fx.official_docx()
    elif label == "HTML bulletin":
        raise RuntimeError("HTML bulletin unavailable")
    elif label == "radar page":
        response.text = fx.RADAR_PAGE
    elif label == "radar image":
        response.content = fx.image_bytes("GIF", (880, 720))
    return response


def fake_render(svg, png_path, chrome_path=""):
    Image.new("RGB", (650, 750), "green").save(png_path)
    return Path(png_path)


def test_full_cycle_offline(tmp_path):
    cfg = Config(nowcast_page_url="http://imd.example/tlng/wx/dist_nowcast.php",
                 output_dir=tmp_path / "output", log_dir=tmp_path / "logs")
    result = pipeline.run_cycle(cfg, session=object(), get=fake_get, render=fake_render)

    assert result.folder == tmp_path / "output" / "2026-09-23" / "2036_IST"
    for name in ("IMD_Nowcast_Bulletin.docx", "radar_max_z.png",
                 "telangana_warning_map.png", "telangana_warning_map.svg", "metadata.json"):
        assert (result.folder / name).is_file()
        assert (tmp_path / "output" / "latest" / name).is_file()

    text = "\n".join(p.text for p in Document(result.bulletin).paragraphs)
    cells = "\n".join(c.text for t in Document(result.bulletin).tables for r in t.rows for c in r.cells)
    assert "District level Nowcast of Telangana" in text
    assert "TIME OF ISSUE: 2026-09-23 (20:36:31 Hrs IST)" in cells
    assert "Valid upto: (23:36:31 Hrs IST)" in cells
    assert "Orange Warning(Be Prepared)" in text and fx.ORANGE_EN in text
    assert "Yellow Warning(Be Updated)" in text and fx.YELLOW_TE in text
    assert "Duty Officer" in text
    meta = json.loads((result.folder / "metadata.json").read_text(encoding="utf-8"))
    assert meta["warning_levels"] == ["orange", "yellow"]


def test_failed_cycle_leaves_no_partial_folder(tmp_path):
    cfg = Config(nowcast_page_url="http://imd.example/x.php", output_dir=tmp_path / "out")

    def broken_get(session, url, *, label, **kw):
        if label == "radar page":
            raise RuntimeError("radar down")
        return fake_get(session, url, label=label, **kw)

    try:
        pipeline.run_cycle(cfg, session=object(), get=broken_get, render=fake_render)
    except RuntimeError:
        pass
    assert not list((tmp_path / "out").rglob("*.partial"))
    assert not (tmp_path / "out" / "2026-09-23" / "2036_IST").exists()


def test_config_requires_url(tmp_path, monkeypatch):
    monkeypatch.delenv("IMD_NOWCAST_URL", raising=False)
    cfg_file = tmp_path / "c.json"
    cfg_file.write_text(json.dumps({"nowcast_page_url": "http://<IMD_SERVER_HOST>/x"}))
    try:
        load_config(cfg_file)
        assert False, "expected ConfigError"
    except ConfigError:
        pass


def test_config_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("IMD_NOWCAST_URL", "http://imd.example/x.php")
    assert load_config(tmp_path / "missing.json").nowcast_page_url == "http://imd.example/x.php"
