#!/usr/bin/env python3
"""
Live data puller. Bypasses MCPs - hits FMP REST + SEC EDGAR directly.
Used for testing without opening a fresh Claude Code session.

Pulls:
- FMP /stable/insider-trading/latest → filter to watchlist insider_watch tickers
- SEC EDGAR submissions → latest 13F per guru CIK

Writes to data/snapshots/ matching SCHEMAS.md.
"""
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import ParseError as XmlParseError

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "snapshots"
DATA.mkdir(parents=True, exist_ok=True)

# Load sibling parse-13f.py module (filename has a hyphen so direct import fails).
_PARSE_13F_PATH = Path(__file__).resolve().parent / "parse-13f.py"
_spec = importlib.util.spec_from_file_location("parse_13f", _PARSE_13F_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"could not load {_PARSE_13F_PATH}")
parse_13f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parse_13f)

WATCHLIST = json.loads((ROOT / "data" / "watchlist.json").read_text())
FMP_KEY = os.environ.get("FMP_API_KEY")
# EDGAR identity is read inside parse_13f from EDGAR_IDENTITY env var.

if not FMP_KEY:
    print("FMP_API_KEY not set. source .env first.", file=sys.stderr)
    sys.exit(1)


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)  # replace() works on Windows when target already exists


def fmp_get(path: str, **params) -> list:
    params["apikey"] = FMP_KEY
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://financialmodelingprep.com{path}?{qs}"
    r = urllib.request.urlopen(url, timeout=30)
    return json.loads(r.read())


def pull_insiders() -> int:
    tickers = WATCHLIST.get("insider_watch", [])
    print(f"pulling insider trades for {tickers}...")
    written = 0
    for ticker in tickers:
        try:
            rows = fmp_get("/stable/insider-trading", symbol=ticker, limit=50)
        except Exception as e:
            print(f"  insider {ticker}: error — {e}")
            rows = []

        trades = []
        for r in rows:
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
        time.sleep(0.2)
    return written


def pull_guru_13f() -> int:
    """Fetch the latest 13F-HR per guru CIK, parse the informationTable XML,
    resolve CUSIPs to tickers, and write holdings-{guru}-{quarter}.json with full positions[].
    """
    written = 0
    for g in WATCHLIST.get("gurus", []):
        try:
            out = parse_13f.pull_guru_13f_full(g["cik"], g["display"], g["id"])
        except (urllib.error.URLError, RuntimeError, XmlParseError, ValueError, KeyError) as e:
            print(f"  13F fail for {g['id']}: {e}")
            continue
        q = out["quarter"] or "latest"
        out_path = DATA / f"holdings-{g['id']}-{q}.json"
        atomic_write(out_path, out)
        n = len(out["positions"])
        total_b = out["total_value_usd"] / 1_000_000_000
        print(f"  {out_path.name}: {n} positions, ${total_b:.1f}B (filed {out['filing_date']})")
        time.sleep(0.15)
        written += 1
    return written


# Back-compat alias: older orchestration code calls pull_guru_13f_metadata().
pull_guru_13f_metadata = pull_guru_13f


def main() -> None:
    print(f"== live pull starting @ {datetime.now().isoformat(timespec='seconds')} ==")
    n_insider = pull_insiders()
    n_13f = pull_guru_13f()
    print(f"== done: {n_insider} insider files, {n_13f} 13F holdings files ==")


if __name__ == "__main__":
    main()
