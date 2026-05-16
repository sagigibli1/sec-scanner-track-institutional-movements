#!/usr/bin/env python3
"""
Derive alerts from snapshots.

Reads insider-*.json, diff-*.json and holdings-*.json from data/snapshots/
and writes data/snapshots/alerts-{date}.json (rolling, latest wins).

After writing, re-runs outputs/dashboard/render.py so the dashboard picks
up the new alerts.

Schema #8 in SCHEMAS.md.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------- Tunables ----------
INSIDER_BUY_USD = 1_000_000            # single buy threshold (severity: success)
INSIDER_SELL_CLUSTER_COUNT = 3         # number of sells to qualify as a cluster
INSIDER_SELL_CLUSTER_USD = 5_000_000   # combined sell value for cluster
INSIDER_SELL_CLUSTER_DAYS = 14         # lookback window in days
NEW_GURU_POSITION_USD = 100_000_000    # new 13F position threshold (severity: info)
GURU_EXIT_USD = 50_000_000             # 13F exited position threshold (severity: warn)
LARGE_INCREASE_DELTA_PCT = 50.0        # increase delta_pct threshold (severity: info)
STALE_FILING_DAYS = 90                 # holdings filing_date age threshold

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "data" / "snapshots"
DASHBOARD_RENDER = ROOT / "outputs" / "dashboard" / "render.py"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def parse_date(s: str):
    """Parse an ISO date string. Returns None on failure."""
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def relpath(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def insider_alerts() -> list[dict]:
    alerts: list[dict] = []
    today = datetime.now(timezone.utc).date()
    for p in sorted(SNAPSHOTS.glob("insider-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        ticker = data.get("ticker", "?")
        trades = data.get("trades", []) or []

        # Single large buy alerts
        for t in trades:
            val = int(t.get("value_usd", 0) or 0)
            action = (t.get("action") or "").lower()
            if action == "buy" and val >= INSIDER_BUY_USD:
                insider = t.get("insider", "פנים")
                date_str = t.get("date", "")
                alerts.append({
                    "tag": "INSIDER BUY",
                    "severity": "success",
                    "text_he": f"{insider} ({ticker}) קנה ${val/1_000_000:.1f}M ב-{date_str}",
                    "ticker": ticker,
                    "value_usd": val,
                    "source_file": relpath(p),
                })

        # Sell cluster: count sells within window + sum
        sells_recent = []
        for t in trades:
            if (t.get("action") or "").lower() != "sell":
                continue
            d = parse_date(t.get("date", ""))
            if d is None:
                continue
            age = (today - d).days
            if 0 <= age <= INSIDER_SELL_CLUSTER_DAYS:
                sells_recent.append(t)
        if len(sells_recent) >= INSIDER_SELL_CLUSTER_COUNT:
            total = sum(int(t.get("value_usd", 0) or 0) for t in sells_recent)
            if total >= INSIDER_SELL_CLUSTER_USD:
                alerts.append({
                    "tag": "INSIDER SELL CLUSTER",
                    "severity": "warn",
                    "text_he": (
                        f"{ticker}: {len(sells_recent)} מכירות פנים ב-{INSIDER_SELL_CLUSTER_DAYS} "
                        f"ימים בסך ${total/1_000_000:.1f}M"
                    ),
                    "ticker": ticker,
                    "value_usd": total,
                    "source_file": relpath(p),
                })
    return alerts


def diff_alerts() -> list[dict]:
    alerts: list[dict] = []
    for p in sorted(SNAPSHOTS.glob("diff-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        guru = data.get("guru", "?")

        for n in data.get("new", []) or []:
            val = int(n.get("value_usd", 0) or 0)
            if val >= NEW_GURU_POSITION_USD:
                tk = n.get("ticker", "?")
                alerts.append({
                    "tag": "NEW GURU POSITION",
                    "severity": "info",
                    "text_he": f"{guru} פתח פוזיציה חדשה ב-{tk} בשווי ${val/1_000_000:.1f}M",
                    "ticker": tk,
                    "value_usd": val,
                    "source_file": relpath(p),
                })

        for ex in data.get("exited", []) or []:
            val = int(ex.get("value_usd", 0) or 0)
            if val >= GURU_EXIT_USD:
                tk = ex.get("ticker", "?")
                alerts.append({
                    "tag": "GURU EXIT",
                    "severity": "warn",
                    "text_he": f"{guru} יצא לגמרי מ-{tk} (${val/1_000_000:.1f}M)",
                    "ticker": tk,
                    "value_usd": val,
                    "source_file": relpath(p),
                })

        for inc in data.get("increased", []) or []:
            delta = float(inc.get("delta_pct", 0) or 0)
            if delta >= LARGE_INCREASE_DELTA_PCT:
                tk = inc.get("ticker", "?")
                alerts.append({
                    "tag": "LARGE POSITION INCREASE",
                    "severity": "info",
                    "text_he": f"{guru} הגדיל את {tk} ב-{delta:.0f}%",
                    "ticker": tk,
                    "value_usd": 0,
                    "source_file": relpath(p),
                })
    return alerts


def stale_alerts() -> list[dict]:
    alerts: list[dict] = []
    today = datetime.now(timezone.utc).date()
    for p in sorted(SNAPSHOTS.glob("holdings-*.json")):
        try:
            data = load_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        filing_date = parse_date(data.get("filing_date", ""))
        if filing_date is None:
            continue
        age = (today - filing_date).days
        if age > STALE_FILING_DAYS:
            guru = data.get("guru_display") or data.get("guru", "?")
            alerts.append({
                "tag": "STALE DATA",
                "severity": "warn",
                "text_he": f"דאטה ישנה: {guru} הגיש לפני {age} ימים ({data.get('filing_date')})",
                "ticker": None,
                "value_usd": 0,
                "source_file": relpath(p),
            })
    return alerts


def run_dashboard_render() -> None:
    if not DASHBOARD_RENDER.exists():
        print(f"warn: dashboard renderer missing at {DASHBOARD_RENDER}", file=sys.stderr)
        return
    subprocess.run(["python3", str(DASHBOARD_RENDER)], check=True)


def main() -> int:
    if not SNAPSHOTS.exists():
        print(f"error: snapshots dir not found: {SNAPSHOTS}", file=sys.stderr)
        return 1

    alerts: list[dict] = []
    alerts.extend(insider_alerts())
    alerts.extend(diff_alerts())
    alerts.extend(stale_alerts())

    now = datetime.now(timezone.utc)
    payload = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "alerts": alerts,
    }

    out_path = SNAPSHOTS / f"alerts-{now.strftime('%Y-%m-%d')}.json"
    atomic_write(out_path, payload)
    print(f"כתב {len(alerts)} התראות אל {relpath(out_path)}")

    run_dashboard_render()
    return 0


if __name__ == "__main__":
    sys.exit(main())
