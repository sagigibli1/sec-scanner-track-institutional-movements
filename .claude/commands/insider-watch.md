---
name: insider-watch
description: סורק טרייד-איזרים של מנכ"לים ובכירים על המניות בווצ'-ליסט (Form 4) ושומר snapshot לכל טיקר
---

# /insider-watch

You are pulling the latest insider transactions (Form 4) for every ticker listed under `insider_watch` in `data/watchlist.json`. Output one snapshot JSON per ticker following schema `insider-{ticker}.json` from `SCHEMAS.md`.

## Inputs

- `data/watchlist.json` (read `insider_watch` array)
- No CLI args.

## Steps

1. Use TodoWrite to create one todo per ticker so the user sees progress.
2. Read `data/watchlist.json`. Extract the `insider_watch` array. If missing or empty, stop and tell the user in Hebrew: "אין טיקרים תחת insider_watch ב-watchlist.json".
3. For each ticker, call the EdgarTools MCP tool `insider_activity` (hosted server) for the last 90 days. If the user is on the local MCP fall back to `edgar_ownership` with the ticker and the Form 4 filter.
   - Always pass tickers in uppercase (e.g. `AAPL` not `Apple`).
   - Always pass dates as ISO `YYYY-MM-DD`.
4. Batch the calls: do NOT exceed 5 EdgarTools calls per ticker. EdgarTools hosted free tier is capped at 100 calls/day total across all commands. If you already see cached snapshots from today under `data/snapshots/insider-{ticker}.json`, prefer those and only refresh tickers whose `as_of` is older than today.
5. Normalize each transaction into the schema:
   - `date` (ISO), `insider` (full name), `role` (CEO / CFO / Director / 10% Owner / ...), `action` ("buy" if transaction code is `P` or net acquired; "sell" if `S` or net disposed).
   - `shares`, `price_usd`, `value_usd = shares * price_usd` (integer USD).
   - `transaction_code` one of `P|S|A|M` (other codes are fine to pass through but document them).
   - `form_url` direct link to the SEC filing.
6. Sort trades within each ticker by `date` desc.
7. Validate the JSON in memory: required keys present, no `null` in `value_usd`, dates are ISO. If invalid, fix before writing.
8. Atomic write: write to `data/snapshots/insider-{ticker}.json.tmp`, then rename to `data/snapshots/insider-{ticker}.json`.
9. Flag the headline trades to the user in Hebrew chat:
   - Buys with `value_usd > 1_000_000` get a green flag line: "קנייה חזקה: {insider} ({role}) ב-{ticker} בסך {value_usd} דולר ב-{date}".
   - Sells with `value_usd > 5_000_000` get a red flag line: "מכירה גדולה: {insider} ({role}) מכר {ticker} בסך {value_usd} דולר ב-{date}".
   - If no flagged trades, say so.

## Output contract

For every ticker in `insider_watch`, exactly one file `data/snapshots/insider-{ticker}.json` matching schema #2 in `SCHEMAS.md`. Even if no trades exist, write the file with `trades: []` and the current date as `as_of`.

## Error handling

- If EdgarTools returns 429 (daily cap hit), stop, write whatever you have so far, and tell the user in Hebrew: "הגענו לתקרה היומית של EdgarTools (100 קריאות). נסה שוב מחר או שדרג ל-Pro".
- If a single ticker fails (bad symbol, no filings), skip it but continue the rest. Log the failure in chat.
- Never delete an existing snapshot. Only overwrite via atomic rename.

## Final chat message (Hebrew)

Show a short summary: how many tickers refreshed, how many trades total, how many flagged buys/sells, list of files written.
