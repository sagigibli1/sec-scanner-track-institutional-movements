---
name: flow-track
description: מושך 13F עדכני של גורו ספציפי (Buffett, Burry, Ackman...) ושומר holdings snapshot
---

# /flow-track {guru_id}

Pull the latest 13F filing for a single guru and write a `holdings-{guru}-{quarter}.json` snapshot per schema #1 in `SCHEMAS.md`.

## Argument

`$1` (required) - guru ID. Must match an `id` in `data/watchlist.json` `gurus` array. Examples:

- `berkshire_hathaway`
- `michael_burry`
- `bill_ackman`

If `$1` is missing or not found in the watchlist, stop and tell the user in Hebrew: "צריך לתת ID של גורו שמופיע ב-watchlist.json. לדוגמא: /flow-track berkshire_hathaway".

## Steps

1. TodoWrite: create todos for "load watchlist", "fetch 13F", "compute tier signals", "validate + write".
2. Read `data/watchlist.json`. Find the guru entry. Extract `cik` and `display`.
3. Pull the latest 13F via EdgarTools MCP. Prefer the hosted tool `institutional_ownership` (filter by the guru's CIK). On local MCP use `edgar_ownership` with the CIK and form type `13F-HR`.
   - Tickers and CIKs in their canonical form (CIK = 10-digit zero-padded string, e.g. `0001067983`).
4. From the filing, extract:
   - `filing_date` (ISO, the date the 13F was accepted by SEC).
   - `quarter` derived from the report period (NOT the filing date). Format `YYYY[Q1-Q4]`.
   - `total_value_usd` - sum of all reported position values.
   - `positions` array: `ticker`, `company`, `shares`, `value_usd`, `pct_of_portfolio` (rounded to 1 decimal), `change_pct` vs previous quarter (if available, else omit the field).
5. Compute `lag_days = (today - filing_date).days`. If `lag_days > 50`, add a Hebrew warning line in chat: "הדוח הזה מ-{filing_date}, כלומר {lag_days} ימים מאחור. הפוזיציות אולי כבר השתנו".
6. If the user implicitly wants weighted-quality classification (most cases do for top gurus), invoke the Institutional Flow Tracker skill to get tier-weighting context. Use the hint phrase that triggers it, for example: "use the institutional-flow-tracker skill to tier this portfolio". The skill uses FMP API (250 calls/day free) so don't double-invoke it for the same guru twice in a session.
7. Set `source` to `"edgartools"` (or `"fmp"` if the only data you got was via the Flow Tracker skill).
8. Validate JSON: all required keys, ISO dates, quarter format, positions sorted by `value_usd` desc.
9. Atomic write to `data/snapshots/holdings-{guru_id}-{quarter}.json.tmp` then rename. Do NOT overwrite if the same file already exists for today's filing_date - tell the user it's already cached and skip.

## Caching rule

Before fetching anything, check if `data/snapshots/holdings-{guru_id}-{quarter}.json` already exists. If yes and its `filing_date` matches what the SEC currently shows as latest, tell the user in Hebrew "הסנאפ כבר קיים מ-{filing_date}, מדלג" and stop. Saves quota.

## Final chat message (Hebrew)

- Filename written.
- `filing_date` + `lag_days` warning if stale.
- Top 5 positions by value (1 line each: `{ticker} {company} - {value_usd} דולר ({pct_of_portfolio}%)`).
- Number of total positions and total portfolio value.

## Error handling

- Unknown guru ID: stop, list available IDs from watchlist.
- 429 from EdgarTools: report quota hit, do not write a partial file.
- FMP failure inside the Flow Tracker skill: continue without tier weighting, set `source: "edgartools"`, note in chat.
