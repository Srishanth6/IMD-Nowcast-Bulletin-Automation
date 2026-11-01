# IMD Nowcast Bulletin Automation

Automated generation of the **District level Nowcast of Telangana** bulletin issued by the
India Meteorological Department (IMD), Meteorological Centre Hyderabad.

Every 3 hours the tool collects the latest nowcast from IMD, downloads the Hyderabad Doppler
radar image and the Telangana district warning map, and builds a ready-to-share Word bulletin
in the official IMD format.

---

## Features

- **Latest nowcast text** – reads the issue time, validity and the Orange / Yellow / Red
  district warnings (English + Telugu) from IMD's own nowcast bulletin. District names are
  never invented; if IMD reports no warnings, its notice is shown instead.
- **Radar image** – finds and downloads the Hyderabad radar **MAX(Z)** product and converts it to PNG.
- **Telangana warning map** – extracts the colour-coded district map from the nowcast page and
  renders it to PNG (headless Chrome/Edge).
- **Bulletin in the IMD format** – IMD header, title, time of issue / valid upto, warning
  blocks, radar + map side by side, Duty Officer line, and the three *Expected Impacts and
  Suggested Measures* pages.
- **Timestamped archive** – each run is saved under `output/<date>/<HHMM>_IST/`, with a copy in
  `output/latest/`.
- **Reliable** – retries with exponential backoff, atomic output folders (no half-written
  runs), a run lock, and rotating logs.
- **Private server address** – the IMD server URL lives only in a git-ignored local config
  and is redacted from every log line.
- **Scheduled** – one PowerShell script registers a Windows Task Scheduler job every 3 hours.

## Bulletin format

| Section | Content |
|---|---|
| Header | Government of India / IMD, Meteorological Centre, Begumpet Airport, Hyderabad (English + Telugu) |
| Title | District level Nowcast of Telangana |
| Times | `TIME OF ISSUE: YYYY-MM-DD (HH:MM:SS Hrs IST)` · `Valid upto: (HH:MM:SS Hrs IST)` (3-hour validity) |
| Warnings | **Orange Warning (Be Prepared)** and **Yellow Warning (Be Updated)**, plus Red when issued – districts in English and Telugu |
| Images | Hyderabad radar MAX(Z) · Telangana district warning map |
| Sign-off | డ్యూటీ అధికారి / ड्यूटी अधिकारी / Duty Officer |
| Pages 2–4 | Expected impacts & suggested measures: moderate thunderstorm/lightning with hail, heavy rain (>15 mm/hr), very severe thunderstorm with squall (>80 km/h) |

## Project structure

```
IMD-Nowcast-Bulletin-Automation/
├── imd_nowcast/
│   ├── config.py        # loads config.local.json / .env (private server URL)
│   ├── net.py           # HTTP session, retries, log redaction
│   ├── nowcast.py       # nowcast page + official bulletin parsing
│   ├── radar.py         # radar MAX(Z) download and PNG conversion
│   ├── warning_map.py   # Telangana SVG map -> PNG
│   ├── bulletin.py      # Word bulletin builder
│   └── pipeline.py      # one complete 3-hourly cycle
├── assets/              # IMD header and expected-impacts pages
├── scripts/
│   ├── setup_task_scheduler.ps1
│   └── remove_task_scheduler.ps1
├── tests/               # offline tests with mocked HTTP
├── run_bulletin.py      # entry point
├── config.example.json
└── requirements.txt
```

Output of each run:

```
output/
├── 2026-09-23/
│   └── 2036_IST/
│       ├── IMD_Nowcast_Bulletin.docx
│       ├── radar_max_z.png
│       ├── telangana_warning_map.png
│       ├── telangana_warning_map.svg
│       └── metadata.json
└── latest/              # copy of the most recent run
```

## Setup (Windows)

```powershell
git clone https://github.com/Srishanth6/IMD-Nowcast-Bulletin-Automation.git
cd IMD-Nowcast-Bulletin-Automation
py -m venv venv
venv\Scripts\pip install -r requirements.txt
copy config.example.json config.local.json
```

Requires Python 3.10+ and Google Chrome or Microsoft Edge (for rendering the warning map).

## Configuration

Edit `config.local.json` (never committed):

| Key | Description |
|---|---|
| `nowcast_page_url` | Full URL of the IMD district nowcast page (`.../tlng/wx/dist_nowcast.php`) on the IMD server |
| `radar_page_url` | IMD Hyderabad radar page (default provided) |
| `output_dir` / `log_dir` | Where bulletins and logs are written |
| `retries`, `retry_backoff_seconds`, `request_timeout` | Network behaviour |
| `chrome_path` | Optional path to Chrome/Edge if not auto-detected |

Alternatively set the `IMD_NOWCAST_URL` environment variable or put it in a `.env` file.

## Usage

```powershell
venv\Scripts\python run_bulletin.py
```

Exit code `0` = success, `1` = cycle failed (see `logs\imd_nowcast.log`), `2` = missing configuration.

## Scheduling (every 3 hours)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_task_scheduler.ps1
```

Registers **IMD Nowcast Bulletin - 3 Hourly** at 00:00, 03:00, 06:00, 09:00, 12:00, 15:00,
18:00 and 21:00 IST. It wakes the laptop, runs missed slots when it becomes available, and retries
up to 3 times. Remove it with `scripts\remove_task_scheduler.ps1`.

## Testing

```powershell
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest
```

All tests run offline using mocked IMD responses.

## Team

| Name | GitHub |
|---|---|
| B. Srishanth Reddy | [@Srishanth6](https://github.com/Srishanth6) |
| Ashmitha (ashmitha-2366) | [@ashmitha-2366](https://github.com/ashmitha-2366) |
| K. Vedanidhi | [@Kvedanidhi](https://github.com/Kvedanidhi) |

## Acknowledgements

Data source: India Meteorological Department, Meteorological Centre Hyderabad.
