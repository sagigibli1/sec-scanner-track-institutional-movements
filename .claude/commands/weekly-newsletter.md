---
name: weekly-newsletter
description: מסכם את ה-7 ימים האחרונים מכל הסנאפים ובוחר 5-10 כותרות עיקריות לניוזלטר בעברית
---

# /weekly-newsletter

Aggregates last 7 days of snapshots and picks 5-10 notable highlights. Writes `newsletter-{YYYY-MM-DD}.json` per schema #5 in `SCHEMAS.md`. Hebrew strings in `headline_he` and `context_he`.

## Inputs

- Everything under `data/snapshots/`. No external API calls.
- No CLI args. Uses today's date.

## Steps

1. TodoWrite: "scan snapshots", "rank candidates", "translate to Hebrew", "validate + write".

2. Define the window:
   - `week_end = today` (ISO).
   - `week_start = today - 6 days` (ISO).
   - File name: `newsletter-{week_start}.json` (using `week_start` keeps weeks discoverable).

3. Build a candidate list of newsworthy events from snapshots:

   a) Insider events. For each `insider-{ticker}.json`, walk `trades`. Keep trades where `date` is between `week_start` and `week_end`. Bucket into:
   - `insider_buy` if `action == "buy"` and `value_usd > 1_000_000`.
   - `insider_sell` if `action == "sell"` and `value_usd > 5_000_000`.

   b) 13F events. For each `diff-{guru}-*.json` whose underlying `to` quarter `filing_date` falls inside the window:
   - Every entry in `new` becomes a `13f_new` candidate.
   - Every entry in `exited` becomes a `13f_exit` candidate.
   - Major `increased` (delta_pct > 25) also becomes `13f_new`-style headlines.

   c) Activist / governance. If any `13D` or `13G` filing JSON exists in the window (future-proofing - the screener may include them later), bucket as `13d_filing`.

   d) Screener signals. From any `screener-*.json` written this week, extract tickers whose `signal` flipped from `hold` or worse to `strong_buy` mid-week - these can become `13f_new` style highlights too.

4. Score each candidate by absolute dollar impact (`value_usd`) and recency. Pick the top 5-10 (never fewer than 3 unless the week is truly empty - in that case write a file with `highlights: []` and tell the user).

5. For each highlight, write:
   - `type` (one of `insider_buy|insider_sell|13f_new|13f_exit|13d_filing`).
   - `ticker`.
   - `guru_or_insider` (display name).
   - `value_usd` (integer).
   - `headline_he` - one-line Hebrew headline in the casual conversational style. Examples:
     - `"באפט הוסיף 2 מיליארד דולר ל-NVDA"`
     - `"מאסק קנה מניות טסלה ב-32 מיליון דולר"`
     - `"ברקשייר יצאה לגמרי מ-HPQ"`
     - `"איקמן פתח פוזיציה חדשה ב-CMG בסך 1.2 מיליארד"`
   - `context_he` - one short Hebrew sentence with the why-care. Examples:
     - `"רבעון ראשון שהוא קונה את המניה"`
     - `"המכירה הגדולה של מאסק מאז ספטמבר"`
     - `"באפט החזיק את המניה 18 רבעונים"`
   - Style rules for Hebrew: no formal/literary words, no "בנוסף" or "כמו כן", no em dashes, write like an Israeli trader explaining to a friend.

6. Sort `highlights` by `value_usd` desc.

7. Validate the JSON: required fields present, Hebrew strings non-empty UTF-8, dates ISO.

8. Atomic write to `data/snapshots/newsletter-{week_start}.json.tmp` then rename.

## Final chat message (Hebrew)

Header: "ניוזלטר שבועי {week_start} עד {week_end}".

For each highlight print one line: `{headline_he} | {context_he}`.

Closing: "הקובץ נשמר ל-data/snapshots/newsletter-{week_start}.json". If the week was empty: "השבוע היה שקט - אין כותרות שעוברות את הסף".

## Error handling

- No snapshots in window: write empty `highlights` array, do not error.
- Corrupt snapshot file: skip it, continue, note in chat.
- This command is read-only against external APIs - no quota concerns.

## Notes

- This command should be runnable end-of-week without burning EdgarTools or FMP quota. Source data must already exist on disk.
- If the user wants fresh data first, tell them to run `/morning-brief` daily through the week, or `/insider-watch` and `/flow-track` for specific gurus before invoking this.
