---
name: thirteen-d
description: מושך 13D ו-13G של מי שמחזיק יותר מ-5% במניה ושומר snapshot של כל בעלי המניות הגדולים
argument-hint: TICKER
---

# /thirteen-d {ticker}

Pull the latest Schedule 13D and 13G filings for a single ticker (entities holding > 5% of the company) and write a `thirteen-d-{ticker}.json` snapshot per schema #6 in `SCHEMAS.md`.

## Argument

`$1` (required) - ticker symbol, uppercase. Examples: `TSLA`, `NVDA`, `META`.

If `$1` is missing, stop and tell the user in Hebrew: "צריך טיקר. לדוגמא: /thirteen-d TSLA".

## Steps

1. TodoWrite: create todos for "fetch 13D/13G filings", "normalize stakeholders", "validate + write".
2. Normalize the ticker to uppercase. If the user passed `tsla`, treat as `TSLA`.
3. Caching check: if `data/snapshots/thirteen-d-{ticker}.json` already exists and its `as_of` equals today's date, tell the user in Hebrew "הסנאפ כבר קיים מהיום, מדלג" and stop. Saves quota.
4. Pull filings via the EdgarTools MCP tool `edgar_tools`. Prefer the hosted tool that filters by form type, e.g. `large_holders` or `ownership_filings` filtered to forms `SC 13D`, `SC 13D/A`, `SC 13G`, `SC 13G/A` for the ticker. On the local MCP fall back to `edgar_ownership` with the ticker and the relevant form list.
   - Always pass tickers in uppercase.
   - Always pass dates as ISO `YYYY-MM-DD`.
   - Look back 24 months. 13D/G are amended often, so keep only the latest filing per filer (latest by `filing_date`).
5. Batch the calls: do NOT exceed 5 EdgarTools calls for this command. EdgarTools hosted free tier is capped at 100 calls/day total across all commands.
6. Normalize each stakeholder into the schema:
   - `filer_name` - full reporting person/entity name.
   - `filer_type` - `"institutional"` if it's a fund / corporation / partnership, `"individual"` if it's a natural person.
   - `filing_type` - `"13D"` or `"13G"` (strip `/A` amendments and treat as the base type).
   - `filing_date` (ISO).
   - `percent_ownership` - rounded to 1 decimal. From the filing's reported beneficial ownership percentage.
   - `shares` - integer beneficial ownership share count.
   - `purpose` - `"activist"` if filing is 13D (active influence intent), `"passive"` if 13G (passive investor exemption), `"unknown"` only if the filing type cannot be determined.
   - `form_url` - direct link to the SEC filing index page.
7. Deduplicate: if the same `filer_name` appears in both a 13D and a 13G in the lookback window, keep only the latest filing. If both share the same date, 13D wins (more recent intent).
8. Sort stakeholders by `percent_ownership` desc.
9. Set `company` to the official issuer name from the filings (e.g. "Tesla Inc"). Set `as_of` to today's date.
10. Validate the JSON in memory: required keys present, no `null` in `percent_ownership` or `shares`, dates are ISO, `filer_type` is one of the allowed values, `filing_type` is `13D` or `13G`. If invalid, fix before writing.
11. Atomic write: write to `data/snapshots/thirteen-d-{ticker}.json.tmp`, then rename to `data/snapshots/thirteen-d-{ticker}.json`.

## Output contract

Exactly one file `data/snapshots/thirteen-d-{ticker}.json` matching schema #6 in `SCHEMAS.md`. If no 5%+ stakeholders exist, still write the file with `stakeholders: []` and the current date as `as_of`.

## Error handling

- If EdgarTools returns 429 (daily cap hit), stop, do not write a partial file, and tell the user in Hebrew: "הגענו לתקרה היומית של EdgarTools (100 קריאות). נסה שוב מחר או שדרג ל-Pro".
- If the ticker is unknown / no filings found, write the file with `stakeholders: []` and tell the user in Hebrew that no 5%+ holders are on file.
- Never delete an existing snapshot. Only overwrite via atomic rename.

## Final chat message (Hebrew)

- Filename written.
- Top 3 stakeholders by `percent_ownership`, one line each: `{filer_name} - {percent_ownership}% ({filing_type})`.
- Activist flag: if any stakeholder has `filing_type: "13D"`, add a red flag line: "דגל אדום: יש 13D פעיל - {filer_name} עם {percent_ownership}%. זה משקיע אקטיביסטי שמתכוון להשפיע על הניהול".
- If only 13G filers exist: "כל הבעלים הגדולים הם פאסיביים (13G). אין אקטיביסטים כרגע".
- If `stakeholders: []`: "אין מחזיקים מעל 5% בדיווח ל-SEC".

## Rules

- Plain hyphen `-` only. No em dashes.
- Tickers always uppercase in filenames and JSON.
- ISO dates only.
