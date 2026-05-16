#!/usr/bin/env python3
"""
Live data puller. Bypasses MCPs - hits FMP REST + SEC EDGAR directly.
Used for testing without opening a fresh Claude Code session.

Pulls:
- FMP /stable/insider-trading/latest → filter to watchlist insider_watch tickers
- SEC EDGAR submissions → latest 13F per guru CIK

Writes to data/snapshots/ matching SCHEMAS.md.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "snapshots"
DATA.mkdir(parents=True, exist_ok=True)

WATCHLIST = json.loads((ROOT / "data" / "watchlist.json").read_text())
FMP_KEY = os.environ.get("FMP_API_KEY")
EDGAR_UA = os.environ.get("EDGAR_IDENTITY", "SEC Scanner contact@example.com")

if not FMP_KEY:
    print("FMP_API_KEY not set. source .env first.", file=sys.stderr)
    sys.exit(1)


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.rename(path)


def fmp_get(path: str, **params) -> list:
    params["apikey"] = FMP_KEY
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://financialmodelingprep.com{path}?{qs}"
    r = urllib.request.urlopen(url, timeout=30)
    return json.loads(r.read())


def edgar_get(path: str) -> dict:
    req = urllib.request.Request(
        f"https://data.sec.gov{path}",
        headers={"User-Agent": EDGAR_UA, "Accept": "application/json"},
    )
    r = urllib.request.urlopen(req, timeout=30)
    return json.loads(r.read())


def pull_insiders() -> int:
    tickers = WATCHLIST.get("insider_watch", [])
    print(f"pulling insider trades for {tickers}...")
    by_ticker: dict[str, list] = {t: [] for t in tickers}
    # free tier: page=0 only. Pull latest 100, filter to watchlist.
    batch = fmp_get("/stable/insider-trading/latest", page=0, limit=100)
    print(f"  pulled {len(batch)} latest filings (free-tier cap)")
    for row in batch:
        sym = row.get("symbol")
        if sym in by_ticker:
            by_ticker[sym].append(row)

    written = 0
    for ticker, rows in by_ticker.items():
        trades = []
        for r in rows[:10]:
            tx_type = r.get("transactionType", "").upper()
            action = "buy" if tx_type.startswith("P") else "sell" if tx_type.startswith("S") else tx_type
            shares = int(r.get("securitiesTransacted", 0) or 0)
            price = float(r.get("price", 0) or 0)
            trades.append({
                "date": r.get("transactionDate", "")[:10],
                "insider": r.get("reportingName", "unknown"),
                "role": r.get("typeOfOwner", ""),
                "action": action,
                "shares": shares,
                "price_usd": price,
                "value_usd": int(shares * price),
                "transaction_code": tx_type[:1] if tx_type else "",
                "form_url": r.get("link", ""),
            })
        out = {
            "ticker": ticker,
            "company": rows[0].get("companyName", ticker) if rows else ticker,
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "trades": trades,
        }
        atomic_write(DATA / f"insider-{ticker}.json", out)
        print(f"  insider-{ticker}.json: {len(trades)} trades")
        written += 1
    return written


def pull_guru_13f_metadata() -> int:
    """SEC EDGAR free path: fetch the latest 13F-HR filing metadata per guru CIK.

    Doesn't parse full 13F holdings table (that needs the filing XML).
    Writes a slim holdings shell with metadata so dashboard can show recency.
    """
    written = 0
    for g in WATCHLIST.get("gurus", []):
        cik = g["cik"].lstrip("0").zfill(10)
        try:
            subs = edgar_get(f"/submissions/CIK{cik}.json")
        except Exception as e:
            print(f"  edgar fail for {g['id']}: {e}")
            continue
        recent = subs.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        # find most recent 13F-HR
        idx = next((i for i, f in enumerate(forms) if f.startswith("13F")), None)
        if idx is None:
            print(f"  no 13F for {g['id']}")
            continue
        filing_date = dates[idx]
        report_date = report_dates[idx]
        q = ""
        if report_date:
            y = report_date[:4]
            m = int(report_date[5:7])
            q = f"{y}Q{(m - 1) // 3 + 1}"
        out = {
            "guru": g["id"],
            "guru_display": g["display"],
            "quarter": q,
            "filing_date": filing_date,
            "source": "sec_edgar_metadata",
            "total_value_usd": 0,
            "positions": [],
            "_note": "metadata only - full positions need XML parse (out of scope for live-pull demo)",
            "accession_number": accession[idx],
        }
        out_path = DATA / f"holdings-{g['id']}-{q or 'latest'}.json"
        atomic_write(out_path, out)
        print(f"  {out_path.name}: filed {filing_date} for {report_date}")
        time.sleep(0.15)  # SEC rate limit politeness
        written += 1
    return written


def main() -> None:
    print(f"== live pull starting @ {datetime.now().isoformat(timespec='seconds')} ==")
    n_insider = pull_insiders()
    n_13f = pull_guru_13f_metadata()
    print(f"== done: {n_insider} insider files, {n_13f} 13F metadata files ==")


if __name__ == "__main__":
    main()
