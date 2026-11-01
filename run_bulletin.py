"""Entry point used by Windows Task Scheduler (every 3 hours)."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from imd_nowcast import net
from imd_nowcast.config import ConfigError, load_config
from imd_nowcast.pipeline import run_cycle


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        return net.redact(super().format(record))


def setup_logging(log_dir) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(log_dir / "imd_nowcast.log", maxBytes=1_000_000,
                                       backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    handlers = [file_handler]
    if sys.stdout:  # pythonw has no console
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        handlers.append(console)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate the IMD Telangana nowcast bulletin")
    parser.add_argument("--config", help="path to config JSON (default: config.local.json)")
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 2
    setup_logging(cfg.log_dir)
    lock = cfg.output_dir / ".imd_run.lock"
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        logging.warning("Another run is in progress; skipping")
        return 0
    try:
        result = run_cycle(cfg)
        logging.info("Done: %s", result.bulletin)
        return 0
    except Exception as error:  # logged, redacted, non-zero exit for Task Scheduler
        logging.error("Bulletin cycle failed: %s", net.redact(error))
        return 1
    finally:
        os.close(fd)
        os.remove(lock)


if __name__ == "__main__":
    raise SystemExit(main())
