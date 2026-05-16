#!/usr/bin/env python3
"""
13F informationTable parser.

End-to-end pipeline per guru CIK:
  1. Hit SEC EDGAR /submissions/CIK{cik}.json -> find latest 13F-HR.
  2. Hit /Archives/edgar/data/{cik_int}/{acc_no_no_hyphens}/index.json -> locate informationTable XML.
  3. Download the XML, cache to disk under data/.cache/13f/.
  4. Parse <infoTable> rows. Aggregate duplicate CUSIPs (same issuer, multiple sub-managers).
  5. Resolve CUSIP -> ticker via OpenFIGI free API (cached to data/.cusip_cache.json).
  6. Compute pct_of_portfolio. Return dict matching SCHEMAS.md schema #1.

Library + CLI. When invoked directly, iterates data/watchlist.json and writes
data/snapshots/holdings-{guru}-{quarter}.json files with full positions[].

stdlib only. SEC EDGAR rate limit 10 req/sec -> 0.15s sleeps. OpenFIGI free tier
25 req/min, 250/day, no key required, batched up to OPENFIGI_BATCH_SIZE cusips per POST.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
CACHE_DIR = DATA / ".cache" / "13f"
CUSIP_CACHE_PATH = DATA / ".cusip_cache.json"

SNAPSHOTS.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

EDGAR_UA = os.environ.get("EDGAR_IDENTITY", "SEC Scanner contact@example.com")
NS_INFOTABLE = "http://www.sec.gov/edgar/document/thirteenf/informationtable"
RATE_SLEEP = 0.15  # seconds between SEC calls (10 req/sec ceiling)

# --------------------------------------------------------------------------- HTTP


def _http_get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    h = {"User-Agent": EDGAR_UA, "Accept-Encoding": "gzip, deflate"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw


def _http_post(url: str, body: bytes, headers: dict | None = None, timeout: int = 30) -> bytes:
    h = {"User-Agent": EDGAR_UA, "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def edgar_submissions(cik: str) -> dict:
    cik10 = cik.lstrip("0").zfill(10)
    raw = _http_get(f"https://data.sec.gov/submissions/CIK{cik10}.json",
                    headers={"Accept": "application/json"})
    return json.loads(raw)


def edgar_filing_index(cik_int: int, accession_no: str) -> dict:
    acc_path = accession_no.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_path}/index.json"
    raw = _http_get(url, headers={"Accept": "application/json"})
    return json.loads(raw)


def edgar_filing_file(cik_int: int, accession_no: str, filename: str) -> bytes:
    acc_path = accession_no.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_path}/{filename}"
    return _http_get(url)


# --------------------------------------------------------------------------- 13F discovery


def find_latest_13f(submissions: dict) -> dict | None:
    """Return {accession, form, filing_date, report_date} for newest 13F-HR or 13F-HR/A."""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accs = recent.get("accessionNumber", [])
    fdates = recent.get("filingDate", [])
    rdates = recent.get("reportDate", [])
    for i, form in enumerate(forms):
        if form.startswith("13F-HR"):
            return {
                "accession": accs[i],
                "form": form,
                "filing_date": fdates[i],
                "report_date": rdates[i] if i < len(rdates) else "",
            }
    return None


def find_information_table(index_json: dict) -> str | None:
    """Locate the informationTable XML inside a filing's index.json directory listing."""
    items = index_json.get("directory", {}).get("item", [])
    names = [it.get("name", "") for it in items]

    # 1. canonical filename patterns
    for n in names:
        low = n.lower()
        if low.endswith(".xml") and ("infotable" in low or "informationtable" in low or "form13f" in low):
            return n

    # 2. fallback: any non-primary xml. primary_doc.xml is the cover page, skip it.
    xmls = [n for n in names if n.lower().endswith(".xml") and n.lower() != "primary_doc.xml"]
    if len(xmls) == 1:
        return xmls[0]
    # ambiguous - try each in size order (biggest first, infotable is usually the big one)
    if xmls:
        by_size = sorted(
            [(it.get("name", ""), int(it.get("size") or 0)) for it in items
             if it.get("name", "") in xmls],
            key=lambda x: -x[1],
        )
        return by_size[0][0] if by_size else None
    return None


# --------------------------------------------------------------------------- XML parse


def _safe_int(raw: str | None) -> int:
    try:
        return int(float(raw or 0))
    except ValueError:
        return 0


def _find_info_tables(root: ET.Element, ns: dict) -> list[ET.Element]:
    """SEC filings vary on namespace declaration. Try canonical, then bare, then localname scan."""
    candidates = root.findall("x:infoTable", ns)
    if not candidates:
        candidates = root.findall("infoTable")
    if not candidates:
        candidates = [el for el in root.iter() if _localname(el.tag) == "infoTable"]
    return candidates


def _extract_row(el: ET.Element, ns: dict) -> dict | None:
    cusip = _findtext(el, "cusip", ns)
    if not cusip:
        return None
    return {
        "cusip": cusip.strip().upper(),
        "name": (_findtext(el, "nameOfIssuer", ns) or "").strip(),
        "title_of_class": (_findtext(el, "titleOfClass", ns) or "").strip(),
        "value_usd": _safe_int(_findtext(el, "value", ns)),
        "shares": _safe_int(_findtext_nested(el, "shrsOrPrnAmt", "sshPrnamt", ns)),
        "share_type": (_findtext_nested(el, "shrsOrPrnAmt", "sshPrnamtType", ns) or "SH").strip(),
    }


def _aggregate_by_cusip(rows: list[dict]) -> list[dict]:
    """Same issuer appears once per sub-manager. Sum value + shares per cusip."""
    agg: dict[str, dict] = {}
    for r in rows:
        key = r["cusip"]
        if key not in agg:
            agg[key] = {
                "cusip": r["cusip"],
                "name": r["name"],
                "title_of_class": r["title_of_class"],
                "value_usd": 0,
                "shares": 0,
                "share_type": r["share_type"],
            }
        agg[key]["value_usd"] += r["value_usd"]
        agg[key]["shares"] += r["shares"]
    out = list(agg.values())
    out.sort(key=lambda x: -x["value_usd"])
    return out


def parse_holdings_xml(xml_text: str) -> list[dict]:
    """Parse infoTable rows from a 13F XML payload. Aggregates duplicate CUSIPs."""
    root = ET.fromstring(xml_text)
    ns = {"x": NS_INFOTABLE}
    rows = [r for r in (_extract_row(el, ns) for el in _find_info_tables(root, ns)) if r]
    return _aggregate_by_cusip(rows)


def _localname(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _findtext(el: ET.Element, name: str, ns: dict) -> str | None:
    node = el.find(f"x:{name}", ns)
    if node is None:
        node = el.find(name)
    if node is None:
        # localname scan
        for child in el:
            if _localname(child.tag) == name:
                return child.text
        return None
    return node.text


def _findtext_nested(el: ET.Element, parent: str, child: str, ns: dict) -> str | None:
    pnode = el.find(f"x:{parent}", ns)
    if pnode is None:
        pnode = el.find(parent)
    if pnode is None:
        for c in el:
            if _localname(c.tag) == parent:
                pnode = c
                break
    if pnode is None:
        return None
    return _findtext(pnode, child, ns)


# --------------------------------------------------------------------------- caching


def _load_cusip_cache() -> dict:
    if CUSIP_CACHE_PATH.exists():
        try:
            return json.loads(CUSIP_CACHE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cusip_cache(cache: dict) -> None:
    tmp = CUSIP_CACHE_PATH.with_suffix(CUSIP_CACHE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False, sort_keys=True))
    tmp.rename(CUSIP_CACHE_PATH)


_cusip_cache_mem: dict | None = None


def _cusip_cache() -> dict:
    global _cusip_cache_mem
    if _cusip_cache_mem is None:
        _cusip_cache_mem = _load_cusip_cache()
    return _cusip_cache_mem


# --------------------------------------------------------------------------- OpenFIGI


def _openfigi_post_attempt(body: bytes, attempt: int) -> tuple[bytes | None, bool]:
    """One POST attempt. Returns (response_or_None, retry_on_429)."""
    url = "https://api.openfigi.com/v3/mapping"
    try:
        return _http_post(url, body), False
    except urllib.error.HTTPError as e:
        if e.code == 429 and attempt == 1:
            return None, True
        print(f"  openfigi http {e.code} (attempt {attempt}): {e}", file=sys.stderr)
        return None, False
    except urllib.error.URLError as e:
        print(f"  openfigi network error (attempt {attempt}): {e}", file=sys.stderr)
        return None, False


def _openfigi_post_with_retry(body: bytes) -> bytes | None:
    """POST to OpenFIGI. On 429, back off 6s and retry once."""
    raw, retry = _openfigi_post_attempt(body, attempt=1)
    if raw is not None or not retry:
        return raw
    time.sleep(6)
    raw, _ = _openfigi_post_attempt(body, attempt=2)
    return raw


def _openfigi_batch(cusips: list[str]) -> dict[str, str | None]:
    """POST a single batch (callers must respect OPENFIGI_BATCH_SIZE). Returns {cusip: ticker_or_None}."""
    if not cusips:
        return {}
    body = json.dumps([{"idType": "ID_CUSIP", "idValue": c} for c in cusips]).encode()
    raw = _openfigi_post_with_retry(body)
    if raw is None:
        return {c: None for c in cusips}
    try:
        results = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  openfigi bad JSON: {e}", file=sys.stderr)
        return {c: None for c in cusips}

    out: dict[str, str | None] = {}
    for cusip, entry in zip(cusips, results):
        if "data" in entry and entry["data"]:
            data = entry["data"]
            # Prefer the US composite. exchCode == "US" or compositeFIGI present.
            pick = None
            for d in data:
                if d.get("exchCode") == "US":
                    pick = d
                    break
            if pick is None:
                # any "Common Stock" or first
                for d in data:
                    if d.get("securityType") == "Common Stock":
                        pick = d
                        break
            if pick is None:
                pick = data[0]
            out[cusip] = pick.get("ticker")
        else:
            out[cusip] = None
    return out


def cusip_to_ticker(cusip: str) -> str | None:
    """Single-cusip lookup, with cache."""
    cusip = (cusip or "").strip().upper()
    if not cusip:
        return None
    cache = _cusip_cache()
    if cusip in cache:
        return cache[cusip]
    result = _openfigi_batch([cusip])
    cache.update(result)
    _save_cusip_cache(cache)
    return cache.get(cusip)


OPENFIGI_BATCH_SIZE = 10  # free tier (no API key) caps each request at 10 IDs


def resolve_tickers_bulk(cusips: list[str]) -> dict[str, str | None]:
    """Bulk resolver. Uses cache. Hits OpenFIGI in small batches with rate-limit pauses."""
    cache = _cusip_cache()
    # Deduplicate to avoid re-asking for the same cusip.
    unknown = list(dict.fromkeys(c for c in cusips if c not in cache))
    if unknown:
        # Free tier ceiling: 25 requests/minute. 2.5s sleep keeps us under that comfortably.
        for i in range(0, len(unknown), OPENFIGI_BATCH_SIZE):
            chunk = unknown[i:i + OPENFIGI_BATCH_SIZE]
            print(f"  openfigi resolving {i + len(chunk)}/{len(unknown)} new cusips...")
            res = _openfigi_batch(chunk)
            cache.update(res)
            _save_cusip_cache(cache)
            if i + OPENFIGI_BATCH_SIZE < len(unknown):
                time.sleep(2.5)
    return {c: cache.get(c) for c in cusips}


# --------------------------------------------------------------------------- caching XML


def _cache_key(cik: str, accession_no: str) -> Path:
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", accession_no)
    return CACHE_DIR / f"{cik.lstrip('0').zfill(10)}-{safe}.xml"


def fetch_filing_xml(cik: str, accession_no: str) -> str:
    """Download (or load cached) informationTable XML for the given filing. Returns XML text."""
    cache_path = _cache_key(cik, accession_no)
    if cache_path.exists() and cache_path.stat().st_size > 200:
        return cache_path.read_text()

    cik_int = int(cik.lstrip("0") or "0")
    idx = edgar_filing_index(cik_int, accession_no)
    time.sleep(RATE_SLEEP)
    name = find_information_table(idx)
    if not name:
        raise RuntimeError(f"no informationTable XML found in filing {accession_no}")
    raw = edgar_filing_file(cik_int, accession_no, name)
    time.sleep(RATE_SLEEP)
    text = raw.decode("utf-8", errors="replace")
    # atomic write
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.rename(cache_path)
    return text


# --------------------------------------------------------------------------- pipeline


def _quarter_from_report_date(report_date: str) -> str:
    if not report_date or len(report_date) < 10:
        return ""
    y = report_date[:4]
    m = int(report_date[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def _rescale_to_dollars(rows: list[dict]) -> None:
    """Pre-2023 13F filings used thousands. Detect via average-price-per-share sanity check
    and rescale in place. A filing where row_value/row_shares < $1 across all rows is in thousands.
    """
    plausible = 0
    suspicious = 0
    for r in rows:
        if r["shares"] <= 0 or r["value_usd"] <= 0:
            continue
        per_share = r["value_usd"] / r["shares"]
        if per_share < 1:
            suspicious += 1
        else:
            plausible += 1
    if suspicious > 0 and plausible == 0:
        for r in rows:
            r["value_usd"] *= 1000


def _build_position(row: dict, ticker: str, total_value: float) -> dict:
    pct = round((row["value_usd"] / total_value) * 100, 2) if total_value else 0.0
    return {
        "ticker": ticker,
        "company": row["name"],
        "cusip": row["cusip"],
        "shares": row["shares"],
        "value_usd": row["value_usd"],
        "pct_of_portfolio": pct,
        "change_pct": None,
    }


def pull_guru_13f_full(cik: str, display_name: str, guru_id: str) -> dict:
    """End-to-end: returns dict matching SCHEMAS.md schema #1, full positions[]."""
    subs = edgar_submissions(cik)
    time.sleep(RATE_SLEEP)
    latest = find_latest_13f(subs)
    if not latest:
        raise RuntimeError(f"no 13F filing for CIK {cik} ({guru_id})")

    accession = latest["accession"]
    filing_date = latest["filing_date"]
    quarter = _quarter_from_report_date(latest["report_date"])

    rows = parse_holdings_xml(fetch_filing_xml(cik, accession))
    _rescale_to_dollars(rows)
    total_value = sum(r["value_usd"] for r in rows)

    tickers = resolve_tickers_bulk([r["cusip"] for r in rows])
    positions = [_build_position(r, tickers.get(r["cusip"]) or "", total_value) for r in rows]

    return {
        "guru": guru_id,
        "guru_display": display_name,
        "quarter": quarter,
        "filing_date": filing_date,
        "source": "sec_edgar_13f_xml",
        "total_value_usd": total_value,
        "positions": positions,
        "accession_number": accession,
    }


# --------------------------------------------------------------------------- CLI


def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.rename(path)


def _load_watchlist() -> dict:
    return json.loads((DATA / "watchlist.json").read_text())


def main() -> int:
    print(f"== parse-13f starting @ {datetime.now(timezone.utc).isoformat(timespec='seconds')} ==")
    print(f"   edgar identity: {EDGAR_UA}")
    watchlist = _load_watchlist()
    written = 0
    for g in watchlist.get("gurus", []):
        cik = g["cik"]
        guru_id = g["id"]
        display = g["display"]
        try:
            out = pull_guru_13f_full(cik, display, guru_id)
        except Exception as e:
            print(f"FAIL: {guru_id} - {e}")
            continue
        q = out["quarter"] or "latest"
        out_path = SNAPSHOTS / f"holdings-{guru_id}-{q}.json"
        _atomic_write_json(out_path, out)
        n = len(out["positions"])
        total_b = out["total_value_usd"] / 1_000_000_000
        unresolved = sum(1 for p in out["positions"] if not p["ticker"])
        print(f"OK: {guru_id} {q} - {n} positions, ${total_b:.1f}B "
              f"({unresolved} cusips unresolved)")
        written += 1
    print(f"== done: {written} holdings files written ==")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
