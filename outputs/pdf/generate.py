"""
PDF report generator (Hebrew RTL, 1-page).

Inputs (read):
  data/snapshots/newsletter-*.json  (latest by name)
  data/snapshots/screener-*.json    (latest by name)

Output:
  outputs/pdf/report-{week}.pdf

Usage:
  python3 generate.py
"""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

try:
    from weasyprint import HTML
except ImportError:
    print(
        "error: weasyprint not installed. run: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "data" / "snapshots"
OUT_DIR = Path(__file__).resolve().parent

SIGNAL_LABEL = {
    "strong_buy": "קנייה חזקה",
    "buy": "קנייה",
    "hold": "החזק",
    "sell": "מכירה",
    "strong_sell": "מכירה חזקה",
}
TYPE_LABEL = {
    "insider_buy": "קניית פנים",
    "insider_sell": "מכירת פנים",
    "13f_new": "פוזיציה חדשה (13F)",
    "13f_exit": "יציאה מפוזיציה (13F)",
    "13d_filing": "הגשת 13D",
}


def load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def build_html(newsletter: dict, screener: dict | None) -> str:
    week_start = newsletter.get("week_start", "?")
    week_end = newsletter.get("week_end", "?")
    highlights = newsletter.get("highlights", [])

    highlight_rows = "\n".join(
        f"""
        <tr>
          <td class="type">{escape(TYPE_LABEL.get(h.get("type"), h.get("type", "-")))}</td>
          <td class="ticker">{escape(h.get("ticker", "-"))}</td>
          <td class="actor">{escape(h.get("guru_or_insider", "-"))}</td>
          <td class="value">{fmt_money(h.get("value_usd"))}</td>
          <td class="headline">
            <div class="hl">{escape(h.get("headline_he", ""))}</div>
            <div class="ctx">{escape(h.get("context_he", ""))}</div>
          </td>
        </tr>"""
        for h in highlights
    )

    screener_block = ""
    if screener:
        rankings = sorted(
            screener.get("rankings", []), key=lambda r: r.get("score", 0), reverse=True
        )[:5]
        rows = "\n".join(
            f"""
            <tr>
              <td class="ticker">{escape(r.get("ticker", "-"))}</td>
              <td class="score">{r.get("score", 0):.1f}</td>
              <td class="signal signal-{escape(r.get("signal", ""))}">{escape(SIGNAL_LABEL.get(r.get("signal", ""), r.get("signal", "")))}</td>
              <td>{escape(r.get("signal_reason", ""))}</td>
            </tr>"""
            for r in rankings
        )
        screener_block = f"""
        <section class="block">
          <h2>סורק - חמישה ראשונים ({escape(screener.get("date", "-"))})</h2>
          <table class="data">
            <thead>
              <tr><th>טיקר</th><th>ניקוד</th><th>איתות</th><th>סיבה</th></tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </section>
        """

    disclaimer = (
        "הקורס הזה הוא חינוך טכנולוגי בלבד. אין כאן ייעוץ השקעות, המלצות קנייה או "
        "מכירה, או חוות דעת על ניירות ערך. כל החלטה היא באחריותך בלבד. הנתונים מבוססים "
        "על מקורות ציבוריים (דיווחי SEC) שמתפרסמים באיחור של עד 45 יום."
    )

    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8" />
<title>דוח שבועי</title>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;900&display=swap" rel="stylesheet" />
<style>
  @page {{ size: A4; margin: 18mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Heebo", system-ui, sans-serif; color: #14171f; font-size: 10pt; line-height: 1.45; direction: rtl; }}
  header {{ border-bottom: 2px solid #14171f; padding-bottom: 8px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: baseline; }}
  header h1 {{ font-size: 18pt; font-weight: 800; margin: 0; }}
  header .week {{ font-size: 10pt; color: #5a6275; }}
  h2 {{ font-size: 12pt; margin: 14px 0 6px; font-weight: 700; }}
  table.data {{ width: 100%; border-collapse: collapse; }}
  table.data th {{ background: #14171f; color: #fff; padding: 6px 8px; text-align: right; font-size: 9pt; font-weight: 600; }}
  table.data td {{ padding: 6px 8px; border-bottom: 1px solid #e6e8ee; text-align: right; vertical-align: top; }}
  .ticker {{ font-family: "SF Mono", Menlo, monospace; font-weight: 700; direction: ltr; unicode-bidi: embed; text-align: right; }}
  .value {{ font-family: "SF Mono", Menlo, monospace; direction: ltr; unicode-bidi: embed; text-align: right; }}
  .headline .hl {{ font-weight: 600; }}
  .headline .ctx {{ color: #5a6275; font-size: 9pt; margin-top: 2px; }}
  .type {{ font-size: 9pt; color: #2557d6; font-weight: 600; }}
  .actor {{ font-size: 9pt; }}
  .score {{ font-weight: 700; }}
  .signal {{ padding: 1px 6px; border-radius: 4px; font-size: 9pt; }}
  .signal-strong_buy, .signal-buy {{ background: #e7f7ec; color: #0f8a3c; }}
  .signal-hold {{ background: #fdf3df; color: #b8770f; }}
  .signal-sell, .signal-strong_sell {{ background: #fde9e9; color: #c43030; }}
  footer {{ position: fixed; bottom: 6mm; right: 14mm; left: 14mm; border-top: 1px solid #e6e8ee; padding-top: 6px; color: #5a6275; font-size: 8pt; line-height: 1.4; }}
</style>
</head>
<body>
<header>
  <h1>מעקב שחקנים גדולים - דוח שבועי</h1>
  <div class="week">{escape(week_start)} עד {escape(week_end)}</div>
</header>

<section class="block">
  <h2>אירועים מרכזיים השבוע</h2>
  <table class="data">
    <thead>
      <tr>
        <th>סוג</th>
        <th>טיקר</th>
        <th>שחקן</th>
        <th>שווי</th>
        <th>תיאור</th>
      </tr>
    </thead>
    <tbody>{highlight_rows}</tbody>
  </table>
</section>

{screener_block}

<footer>
  <strong>דיסקליימר:</strong> {escape(disclaimer)}
</footer>
</body>
</html>"""


def find_latest(pattern: str) -> Path | None:
    files = sorted(SNAPSHOTS.glob(pattern))
    return files[-1] if files else None


def main() -> int:
    nl_path = find_latest("newsletter-*.json")
    if nl_path is None:
        print("error: no newsletter snapshots found", file=sys.stderr)
        return 1
    newsletter = load_json(nl_path)

    sc_path = find_latest("screener-*.json")
    screener = load_json(sc_path) if sc_path else None

    html = build_html(newsletter, screener)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # derive week token from newsletter filename: newsletter-2026-W20.json -> 2026-W20
    stem = nl_path.stem.replace("newsletter-", "")
    out = OUT_DIR / f"report-{stem}.pdf"
    tmp = out.with_suffix(".pdf.tmp")
    HTML(string=html, base_url=str(OUT_DIR)).write_pdf(str(tmp))
    tmp.replace(out)
    print(f"ok: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
