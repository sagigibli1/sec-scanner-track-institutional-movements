---
name: morning-brief
description: הסקירה היומית - מצליב Form 4, שינויים ב-13F ואיתותי Institutional Flow ומחזיר טופ 5 טיקרים
---

# /morning-brief

Daily orchestrator. Crosses insider activity, 13F portfolio changes, and Institutional Flow Tracker signals across the full watchlist. Writes `screener-{YYYY-MM-DD}.json` per schema #4 in `SCHEMAS.md` and prints the top 5 ranked tickers in Hebrew chat.

## Inputs

- `data/watchlist.json` (uses `tickers` and `gurus` arrays).
- All snapshots under `data/snapshots/` from prior commands.

## Steps

1. TodoWrite the plan: "load watchlist", "refresh insider for hot tickers", "scan recent 13F snapshots", "run Flow Tracker screen", "score + rank", "write file", "Hebrew summary".

2. Read `data/watchlist.json`. The screener universe = `tickers`.

3. Insider layer:
   - For each ticker in `tickers`, look for `data/snapshots/insider-{ticker}.json`. If missing or older than today, decide whether to refresh it.
   - To stay under the 100/day EdgarTools cap, ONLY refresh the top ~10 tickers (by combined market interest). Tell the user how many you refreshed vs cached.
   - If you need a full refresh, suggest in Hebrew that the user run `/insider-watch` first instead of doing it inline.
   - Per ticker, count `buys_30d` and `sells_30d` from the trades array.

4. 13F layer:
   - For each guru in `gurus`, look at the latest two `holdings-{guru}-*.json` snapshots already on disk.
   - If a guru has zero snapshots, skip them and note it.
   - For each ticker in the watchlist, collect which gurus hold it now AND which gurus added or initiated it in the most recent diff (use existing `diff-*.json` files if present).

5. Flow Tracker layer:
   - Invoke the Institutional Flow Tracker skill with a screen across the watchlist tickers. Hint phrase: "use institutional-flow-tracker skill to screen these tickers for QoQ accumulation: {comma list}".
   - The skill returns a signal per ticker: `strong_buy | buy | hold | sell | strong_sell` and a reason string.
   - Budget: one skill invocation total per `/morning-brief` run (FMP free tier is 250/day).

6. Score and rank:
   - Compose a single score per ticker on a 0-10 scale.
   - Suggested weights (tweak if obviously wrong):
     - Flow Tracker signal: strong_buy=5, buy=3, hold=1, sell=-2, strong_sell=-4.
     - Insider net flow: `+1` per insider buy in last 30 days (cap at +3), `-1` per insider sell over $5M (cap at -3).
     - Guru participation: `+1` per superinvestor (Berkshire/Burry/Ackman tier) currently holding, `+2` if they ADDED last quarter.
   - Clamp final score to `[0, 10]`.
   - Map score back to a `signal` field for the rankings JSON (the schema requires this) using the Flow Tracker classification as the primary signal, not the numeric score.

7. Build the `screener-{date}.json` object:
   - `date` = today ISO.
   - `watchlist` = the tickers array used.
   - `rankings` = full list sorted by `score` desc. Each entry: `ticker`, `score`, `signal`, `signal_reason` (1-line English from Flow Tracker), `top_buyers` (max 3 guru display names that hold or added), `insider_recent` `{buys_30d, sells_30d}`.

8. Stale-data check: include `lag_days` against the freshest 13F `filing_date` used. If `> 50`, add a Hebrew warning in chat.

9. Validate the JSON. Atomic write to `data/snapshots/screener-{YYYY-MM-DD}.json.tmp` then rename.

## Final chat message (Hebrew)

Header: "בריף של {date}".

Top 5 ranked tickers as a clean numbered list. Each line:

`{rank}. {ticker} - {signal_he} ({score}/10) | {1-line reason in Hebrew} | פנימיים: {buys_30d} קניות / {sells_30d} מכירות`

Signal translations: strong_buy = "קנייה חזקה", buy = "קנייה", hold = "החזק", sell = "מכירה", strong_sell = "מכירה חזקה".

Closing line: "כתבתי את הסנאפ ל-{filename}. רוץ /weekly-newsletter בסוף השבוע לסיכום".

## Error handling

- EdgarTools quota hit mid-run: write the file with whatever data you have, mark missing tickers with `signal: "hold"` and a reason "data unavailable today", warn the user in Hebrew.
- Flow Tracker skill not installed or fails: continue with the insider + 13F layers only and reduce the weighting; note in chat.
- Empty watchlist: stop with a Hebrew error.
