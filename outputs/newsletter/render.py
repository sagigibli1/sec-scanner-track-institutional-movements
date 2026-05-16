"""
Newsletter renderer.

Inputs (read):
  data/snapshots/newsletter-*.json  (latest by name)
  outputs/newsletter/template.md.j2

Output:
  data/reports/newsletter-{week}.md

Usage:
  python3 render.py
  python3 render.py --file data/snapshots/newsletter-2026-W20.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    print(
        "error: jinja2 not installed. run: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOTS = ROOT / "data" / "snapshots"
REPORTS = ROOT / "data" / "reports"

TYPE_LABEL = {
    "insider_buy": "קניית פנים (Form 4)",
    "insider_sell": "מכירת פנים (Form 4)",
    "13f_new": "פוזיציה חדשה (13F)",
    "13f_exit": "יציאה מפוזיציה (13F)",
    "13d_filing": "הגשת 13D",
}


def fmt_money(v: float | int | None) -> str:
    if v is None:
        return "-"
    v = float(v)
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def type_label(t: str) -> str:
    return TYPE_LABEL.get(t, t)


def load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def latest_newsletter() -> Path | None:
    files = sorted(SNAPSHOTS.glob("newsletter-*.json"))
    return files[-1] if files else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="explicit newsletter JSON path")
    args = parser.parse_args()

    nl_path = Path(args.file) if args.file else latest_newsletter()
    if nl_path is None or not nl_path.exists():
        print("error: no newsletter snapshot found", file=sys.stderr)
        return 1

    try:
        data = load_json(nl_path)
    except (json.JSONDecodeError, OSError) as e:
        print(f"error: failed to read {nl_path}: {e}", file=sys.stderr)
        return 1

    env = Environment(
        loader=FileSystemLoader(str(HERE)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        autoescape=False,
    )
    env.globals["fmt_money"] = fmt_money
    env.globals["type_label"] = type_label

    template = env.get_template("template.md.j2")
    rendered = template.render(**data)

    REPORTS.mkdir(parents=True, exist_ok=True)
    stem = nl_path.stem.replace("newsletter-", "")
    out = REPORTS / f"newsletter-{stem}.md"
    tmp = out.with_suffix(".md.tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.replace(out)
    print(f"ok: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
