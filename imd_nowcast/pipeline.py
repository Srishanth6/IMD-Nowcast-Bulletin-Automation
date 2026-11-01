"""One bulletin cycle: fetch -> save timestamped inputs -> build bulletin."""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import net
from .bulletin import build_bulletin
from .config import Config
from .nowcast import fetch_nowcast
from .radar import download_radar
from .warning_map import render_svg_to_png

log = logging.getLogger(__name__)


@dataclass
class CycleResult:
    folder: Path
    bulletin: Path
    radar: Path
    warning_map: Path


def run_cycle(cfg: Config, session=None, get=net.get_with_retries, render=render_svg_to_png) -> CycleResult:
    session = session or net.make_session()

    log.info("Fetching Telangana district nowcast")
    page_html, nowcast = fetch_nowcast(session, cfg, get)
    log.info("IMD issue time %s, valid up to %s", nowcast.issued, nowcast.valid)

    folder = cfg.output_dir / f"{nowcast.issued:%Y-%m-%d}" / f"{nowcast.issued:%H%M}_IST"
    staging = folder.with_name(folder.name + ".partial")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        log.info("Downloading Hyderabad radar MAX(Z) image")
        radar = staging / "radar_max_z.png"
        radar.write_bytes(download_radar(session, cfg, get))

        log.info("Rendering Telangana warning map")
        svg = staging / "telangana_warning_map.svg"
        svg.write_text(nowcast.map_svg, encoding="utf-8")
        warning_map = render(nowcast.map_svg, staging / "telangana_warning_map.png", cfg.chrome_path)

        bulletin = build_bulletin(nowcast, radar, warning_map, staging / "IMD_Nowcast_Bulletin.docx")
        (staging / "metadata.json").write_text(json.dumps({
            "issued_ist": nowcast.issued.isoformat(),
            "valid_ist": nowcast.valid.isoformat(),
            "warning_levels": sorted(k for k, v in nowcast.warnings.items() if v.english or v.telugu),
        }, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    shutil.rmtree(folder, ignore_errors=True)
    staging.rename(folder)
    latest = cfg.output_dir / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    for item in folder.iterdir():
        shutil.copyfile(item, latest / item.name)
    log.info("Bulletin saved to %s", folder)
    return CycleResult(folder, folder / bulletin.name, folder / radar.name, folder / Path(warning_map).name)
