"""
Daily screener - terminal-friendly colored Hebrew table.

Input (read):
  data/snapshots/screener-{date}.json  (latest by name)

Usage:
  python3 daily.py
  python3 daily.py --date 2026-05-17
  python3 daily.py --no-color
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path

try:
    from colorama import Fore, Style, init as colorama_init
except ImportError:
    print(
        "error: colorama not installed. run: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "data" / "snapshots"

SIGNAL_LABEL = {
    "strong_buy": "קנייה חזקה",
    "buy": "קנייה",
    "hold": "החזק",
    "sell": "מכירה",
    "strong_sell": "מכירה חזקה",
}
SIGNAL_COLOR = {
    "strong_buy": "GREEN_BOLD",
    "buy": "GREEN",
    "hold": "YELLOW",
    "sell": "RED",
    "strong_sell": "RED_BOLD",
}


def color(name: str, text: str, enabled: bool) -> str:
    if not enabled:
        return text
    table = {
        "GREEN": Fore.GREEN,
        "GREEN_BOLD": Style.BRIGHT + Fore.GREEN,
        "YELLOW": Fore.YELLOW,
        "RED": Fore.RED,
        "RED_BOLD": Style.BRIGHT + Fore.RED,
        "CYAN": Fore.CYAN,
        "DIM": Style.DIM,
        "BOLD": Style.BRIGHT,
    }
    return f"{table.get(name, '')}{text}{Style.RESET_ALL}"


def visual_width(s: str) -> int:
    """Approximate display width handling Hebrew/wide characters."""
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        elif unicodedata.category(ch).startswith("C"):
            continue
        else:
            w += 1
    return w


def pad(s: str, width: int, align: str = "right") -> str:
    w = visual_width(s)
    if w >= width:
        return s
    space = " " * (width - w)
    return space + s if align == "right" else s + space


def latest_screener() -> Path | None:
    files = sorted(SNAPSHOTS.glob("screener-*.json"))
    return files[-1] if files else None


def load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="screener date (YYYY-MM-DD)")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    use_color = (not args.no_color) and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    colorama_init(strip=not use_color)

    if args.date:
        path = SNAPSHOTS / f"screener-{args.date}.json"
    else:
        path = latest_screener()

    if path is None or not path.exists():
        print("error: no screener snapshot found", file=sys.stderr)
        return 1

    try:
        data = load_json(path)
    except (json.JSONDecodeError, OSError) as e:
        print(f"error: failed to read {path}: {e}", file=sys.stderr)
        return 1

    rankings = sorted(data.get("rankings", []), key=lambda r: r.get("score", 0), reverse=True)
    title = f"סורק יומי - {data.get('date', '?')}"
    print()
    print(color("BOLD", title, use_color))
    print(color("DIM", "=" * 70, use_color))

    headers = ["טיקר", "ניקוד", "איתות", "פנים 30 יום", "קונים מובילים", "סיבה"]
    widths = [8, 7, 14, 14, 24, 40]

    header_line = "  ".join(pad(h, w, "right") for h, w in zip(headers, widths))
    print(color("BOLD", header_line, use_color))
    print(color("DIM", "-" * 70, use_color))

    for r in rankings:
        signal = r.get("signal", "")
        signal_he = SIGNAL_LABEL.get(signal, signal)
        signal_str = color(SIGNAL_COLOR.get(signal, ""), pad(signal_he, widths[2], "right"), use_color)

        insider = r.get("insider_recent") or {}
        buys = insider.get("buys_30d", 0)
        sells = insider.get("sells_30d", 0)
        ins_text = f"+{buys} / -{sells}"
        if buys > 0:
            ins_text = color("GREEN", ins_text, use_color)
        elif sells > 0:
            ins_text = color("RED", ins_text, use_color)

        ticker_str = color("CYAN", pad(r.get("ticker", "-"), widths[0], "right"), use_color)
        score_str = pad(f"{r.get('score', 0):.1f}", widths[1], "right")
        buyers = ", ".join(r.get("top_buyers", [])) or "-"
        reason = r.get("signal_reason", "")[:80]

        print(
            f"{ticker_str}  {score_str}  {signal_str}  "
            f"{pad(ins_text, widths[3], 'right')}  "
            f"{pad(buyers, widths[4], 'right')}  "
            f"{reason}"
        )

    print(color("DIM", "-" * 70, use_color))
    print(
        color(
            "DIM",
            "תזכורת: זה לא ייעוץ השקעות. הנתונים מבוססים על דיווחי SEC ציבוריים.",
            use_color,
        )
    )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
