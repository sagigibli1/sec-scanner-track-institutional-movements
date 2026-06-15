"""
Dashboard render.

Reads latest snapshots from data/snapshots/ and aggregates them into 4 JSON
files inside outputs/dashboard/data/ which the static index.html fetches.

Inputs (read):
  data/snapshots/insider-*.json     -> outputs/dashboard/data/insiders.json
  data/snapshots/diff-*.json        -> outputs/dashboard/data/flows.json
  data/snapshots/screener-*.json    -> outputs/dashboard/data/watchlist.json
  data/snapshots/holdings-*.json    +
  data/snapshots/insider-*.json     -> outputs/dashboard/data/alerts.json (derived)

Usage:
  python3 render.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "data" / "snapshots"
WATCHLIST_PATH = ROOT / "data" / "watchlist.json"
OUT_DIR = Path(__file__).resolve().parent / "data"


def load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def gather_insiders(days: int = 90) -> dict:
    """Aggregate trades from all insider-*.json files in the last `days`."""
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    rows: list[dict] = []
    for p in sorted(SNAPSHOTS.glob("insider-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError) as e:
            print(f"warn: skip {p.name}: {e}", file=sys.stderr)
            continue
        ticker = data.get("ticker", "?")
        company = data.get("company", "")
        for t in data.get("trades", []):
            try:
                dt = datetime.strptime(t["date"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue
            if dt < cutoff:
                continue
            rows.append(
                {
                    "date": t["date"],
                    "ticker": ticker,
                    "company": company,
                    "insider": t.get("insider", "-"),
                    "role": t.get("role"),
                    "action": t.get("action"),
                    "shares": t.get("shares"),
                    "value_usd": t.get("value_usd"),
                    "form_url": t.get("form_url"),
                }
            )
    rows.sort(key=lambda r: r["date"], reverse=True)
    return {"generated_at": datetime.utcnow().isoformat() + "Z", "trades": rows[:100]}


def gather_flows(top_n: int = 5) -> dict:
    """Pull top N institutional changes across all diff snapshots."""
    guru_display: dict[str, str] = {}
    if WATCHLIST_PATH.exists():
        wl = load_json(WATCHLIST_PATH)
        for g in wl.get("gurus", []):
            guru_display[g["id"]] = g["display"]

    items: list[dict] = []
    for p in sorted(SNAPSHOTS.glob("diff-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError) as e:
            print(f"warn: skip {p.name}: {e}", file=sys.stderr)
            continue
        guru = data.get("guru", "?")
        display = guru_display.get(guru, guru)

        for n in data.get("new", []):
            items.append(
                {
                    "guru": guru,
                    "guru_display": display,
                    "ticker": n["ticker"],
                    "change_type": "new",
                    "value_usd": n.get("value_usd", 0),
                    "delta_pct": 100.0,
                    "_sort": n.get("value_usd", 0),
                }
            )
        for e in data.get("exited", []):
            items.append(
                {
                    "guru": guru,
                    "guru_display": display,
                    "ticker": e["ticker"],
                    "change_type": "exited",
                    "value_usd": e.get("value_usd", 0),
                    "delta_pct": -100.0,
                    "_sort": e.get("value_usd", 0),
                }
            )
        for inc in data.get("increased", []):
            items.append(
                {
                    "guru": guru,
                    "guru_display": display,
                    "ticker": inc["ticker"],
                    "change_type": "increased",
                    "value_usd": 0,
                    "delta_pct": inc.get("delta_pct", 0),
                    "_sort": abs(inc.get("delta_pct", 0)) * 1_000_000,
                }
            )
        for dec in data.get("decreased", []):
            items.append(
                {
                    "guru": guru,
                    "guru_display": display,
                    "ticker": dec["ticker"],
                    "change_type": "decreased",
                    "value_usd": 0,
                    "delta_pct": dec.get("delta_pct", 0),
                    "_sort": abs(dec.get("delta_pct", 0)) * 1_000_000,
                }
            )

    items.sort(key=lambda x: x["_sort"], reverse=True)
    for it in items:
        it.pop("_sort", None)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "changes": items[:top_n],
    }


def gather_watchlist() -> dict:
    """Return the most recent screener output."""
    files = sorted(SNAPSHOTS.glob("screener-*.json"))
    if not files:
        return {"generated_at": datetime.utcnow().isoformat() + "Z", "rankings": []}
    latest = files[-1]
    try:
        data = load_json(latest)
    except (json.JSONDecodeError, OSError) as e:
        print(f"warn: failed to read {latest.name}: {e}", file=sys.stderr)
        return {"generated_at": datetime.utcnow().isoformat() + "Z", "rankings": []}
    rankings = list(data.get("rankings", []))
    rankings.sort(key=lambda r: r.get("score", 0), reverse=True)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "date": data.get("date"),
        "rankings": rankings,
    }


def derive_alerts() -> dict:
    """Generate Hebrew alerts from the latest insider trades and diff snapshots."""
    alerts: list[dict] = []

    # Insider activity alerts
    for p in sorted(SNAPSHOTS.glob("insider-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        ticker = data.get("ticker", "?")
        for t in data.get("trades", []):
            val = t.get("value_usd", 0) or 0
            if t.get("action") == "buy" and val >= 1_000_000:
                alerts.append(
                    {
                        "severity": "success",
                        "tag": "קנייה מנכל",
                        "ticker": ticker,
                        "text_he": f"{t.get('insider', 'פנים')} ({t.get('role', '')}) קנה ב-{val / 1_000_000:.1f}M דולר",
                    }
                )
            elif t.get("action") == "sell" and val >= 10_000_000:
                alerts.append(
                    {
                        "severity": "warn",
                        "tag": "מכירת פנים",
                        "ticker": ticker,
                        "text_he": f"{t.get('insider', 'פנים')} ({t.get('role', '')}) מכר ב-{val / 1_000_000:.1f}M דולר",
                    }
                )

    # Institutional moves
    for p in sorted(SNAPSHOTS.glob("diff-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        guru = data.get("guru", "?")
        for n in data.get("new", []):
            val = n.get("value_usd", 0) or 0
            if val >= 500_000_000:
                alerts.append(
                    {
                        "severity": "info",
                        "tag": "פוזיציה חדשה",
                        "ticker": n.get("ticker"),
                        "text_he": f"{guru} פתח פוזיציה חדשה ב-{n.get('ticker')} בשווי {val / 1_000_000_000:.2f}B דולר",
                    }
                )
        for ex in data.get("exited", []):
            alerts.append(
                {
                    "severity": "warn",
                    "tag": "יציאה מפוזיציה",
                    "ticker": ex.get("ticker"),
                    "text_he": f"{guru} מכר את כל הפוזיציה ב-{ex.get('ticker')}",
                }
            )

    return {"generated_at": datetime.utcnow().isoformat() + "Z", "alerts": alerts[:10]}


def main() -> int:
    if not SNAPSHOTS.exists():
        print(f"error: snapshots dir not found: {SNAPSHOTS}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write(OUT_DIR / "insiders.json", gather_insiders())
    atomic_write(OUT_DIR / "flows.json", gather_flows())
    atomic_write(OUT_DIR / "watchlist.json", gather_watchlist())
    atomic_write(OUT_DIR / "alerts.json", derive_alerts())

    print(f"ok: wrote 4 files to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
