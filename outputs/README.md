# Renderers - SEC Scanner

All renderers read from `data/snapshots/` (schema in `../SCHEMAS.md`) and write
to either `data/reports/` or `outputs/<renderer>/`.

## Folder map

```
outputs/
  dashboard/    static RTL Hebrew dashboard (HTML + CSS + vanilla JS)
  excel/        openpyxl Excel workbooks per guru
  pdf/          weasyprint 1-page weekly PDF report
  newsletter/   Jinja Markdown weekly newsletter
  screener/     terminal Hebrew screener with colorama
```

## Install (once, on the user's machine)

```bash
pip install -r outputs/excel/requirements.txt
pip install -r outputs/pdf/requirements.txt
pip install -r outputs/newsletter/requirements.txt
pip install -r outputs/screener/requirements.txt
```

The dashboard has zero Python deps (vanilla JS) - `render.py` uses stdlib only.

## How to run each renderer

### 1. Dashboard (static HTML)

```bash
python3 outputs/dashboard/render.py
# then serve the folder (any static server works):
python3 -m http.server 8080 --directory outputs/dashboard
# open http://127.0.0.1:8080
```

`render.py` reads from `data/snapshots/` and writes 4 JSON files to
`outputs/dashboard/data/` (`insiders.json`, `flows.json`, `watchlist.json`,
`alerts.json`). The page fetches them on load. Re-run after every snapshot
refresh. Light/dark toggle is persisted to `localStorage`.

### 2. Excel workbooks

```bash
python3 outputs/excel/generate.py                       # all gurus, latest quarter
python3 outputs/excel/generate.py --guru michael_burry  # single guru
```

Writes `outputs/excel/{guru}-{quarter}.xlsx` with 3 sheets:
`Current Holdings`, `Quarterly Changes`, `Top Movers`.

### 3. PDF weekly report

```bash
python3 outputs/pdf/generate.py
```

Reads the latest `newsletter-*.json` + `screener-*.json` and writes
`outputs/pdf/report-{week}.pdf`. 1 page, Hebrew RTL, Heebo font via Google Fonts.

### 4. Newsletter (Markdown)

```bash
python3 outputs/newsletter/render.py
python3 outputs/newsletter/render.py --file data/snapshots/newsletter-2026-W20.json
```

Writes `data/reports/newsletter-{week}.md`.

### 5. Daily screener (terminal)

```bash
python3 outputs/screener/daily.py
python3 outputs/screener/daily.py --date 2026-05-17
python3 outputs/screener/daily.py --no-color
```

Colored Hebrew table printed to stdout. Use `--no-color` for piping or
non-tty environments. Auto-disables color when `NO_COLOR` env var is set.

## Test fixtures

Mock JSON files matching every schema are committed under `data/snapshots/`
and `data/watchlist.json`. Re-running any renderer against the mocks is the
quickest smoke test:

```bash
python3 outputs/dashboard/render.py
python3 outputs/excel/generate.py
python3 outputs/newsletter/render.py
python3 outputs/screener/daily.py --no-color
# PDF (needs weasyprint installed):
python3 outputs/pdf/generate.py
```

All renderers are idempotent - re-running overwrites previous output cleanly
via atomic write (`.tmp` then rename).

## Notes

- All renderers are stdlib + the deps listed in their `requirements.txt`.
- All Hebrew strings UTF-8. All dates ISO 8601. All money values USD.
- Disclaimer footer is hardcoded into every visible artifact (dashboard,
  PDF, newsletter). Source: `../legal/disclaimer-he.md`.
