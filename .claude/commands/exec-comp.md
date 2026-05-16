---
name: exec-comp
description: מושך DEF 14A (proxy statement) ושולף שכר של המנכ"ל ו-5 הבכירים הכי משולמים, כולל יחס לעובד החציוני
argument-hint: TICKER
---

# /exec-comp {ticker}

Pull the latest DEF 14A proxy statement for a single ticker and write an `exec-comp-{ticker}.json` snapshot per schema #7 in `SCHEMAS.md`. The file contains compensation details for the CEO and the top 5 named executive officers (NEOs).

## Argument

`$1` (required) - ticker symbol, uppercase. Examples: `NVDA`, `AAPL`, `MSFT`.

If `$1` is missing, stop and tell the user in Hebrew: "צריך טיקר. לדוגמא: /exec-comp NVDA".

## Steps

1. TodoWrite: create todos for "fetch DEF 14A", "extract NEO comp table", "validate + write".
2. Normalize the ticker to uppercase.
3. Caching check: if `data/snapshots/exec-comp-{ticker}.json` already exists and its `filing_date` matches what the SEC currently shows as the latest DEF 14A for this issuer, tell the user in Hebrew "הסנאפ כבר קיים עם אותו filing_date, מדלג" and stop. Saves quota.
4. Pull the latest DEF 14A via the EdgarTools MCP. Prefer the hosted tool `proxy_statement` or `financial_filings` filtered to form type `DEF 14A` for the ticker. On the local MCP fall back to `edgar_filings` with form type `DEF 14A` sorted by `filing_date` desc, take the most recent one.
   - Always pass tickers in uppercase.
   - Always pass dates as ISO `YYYY-MM-DD`.
5. Batch the calls: do NOT exceed 4 EdgarTools calls for this command (1 for filings index, up to 3 for fetching/parsing the proxy document). EdgarTools hosted free tier is capped at 100 calls/day total across all commands.
6. From the proxy statement, locate the Summary Compensation Table (SCT). Extract the CEO row plus the top 5 NEOs (typically: CEO, CFO, and the next 3 highest-paid officers). For each executive emit:
   - `name` - full name.
   - `title` - the role title as printed in the proxy (e.g. "CEO", "CFO", "President and COO").
   - `salary_usd` - integer USD, base salary column.
   - `bonus_usd` - integer USD, bonus column. Use `0` if not disclosed.
   - `stock_awards_usd` - integer USD, stock awards column.
   - `option_awards_usd` - integer USD, option awards column. Use `0` if not disclosed.
   - `total_comp_usd` - integer USD, total column (this is the SCT total, includes the items above plus non-equity incentive, pension, all-other-comp).
7. Set `fiscal_year` to the most recent fiscal year reported in the SCT (integer, e.g. `2025`).
8. Set `filing_date` to the ISO date the DEF 14A was filed.
9. Set `form_url` to the direct SEC link for the filing index.
10. Optional: if the proxy discloses the CEO-to-median-employee pay ratio under Item 402(u), capture the median employee total compensation as `median_employee_total_comp_usd` and the ratio as `ceo_pay_ratio` (e.g. `123` meaning 123:1). These two fields are optional. Only include them if the proxy actually discloses them.
11. Validate the JSON in memory: required keys present, no `null` in `salary_usd` / `total_comp_usd`, dates are ISO, `fiscal_year` is an integer, all USD amounts are non-negative integers, exactly 1 to 6 executives in the array. If invalid, fix before writing.
12. Atomic write: write to `data/snapshots/exec-comp-{ticker}.json.tmp`, then rename to `data/snapshots/exec-comp-{ticker}.json`.

## Output contract

Exactly one file `data/snapshots/exec-comp-{ticker}.json` matching schema #7 in `SCHEMAS.md`. The `executives` array must contain at least the CEO. If the proxy lists fewer than 6 NEOs, include all of them.

## Error handling

- If EdgarTools returns 429 (daily cap hit), stop, do not write a partial file, and tell the user in Hebrew: "הגענו לתקרה היומית של EdgarTools (100 קריאות). נסה שוב מחר או שדרג ל-Pro".
- If no DEF 14A exists for the ticker (small filer, foreign issuer), stop and tell the user in Hebrew "לא נמצא DEF 14A עבור {ticker}. יכול להיות שזה foreign private issuer (20-F) או שהחברה לא מגישה proxy".
- If the SCT can be located but a column is missing for a specific executive (common for first-year hires), set that column to `0` and continue.
- Never delete an existing snapshot. Only overwrite via atomic rename.

## Final chat message (Hebrew)

- Filename written.
- Filing date + fiscal year covered.
- CEO total compensation in one line: "המנכ"ל {name} קיבל {total_comp_usd} דולר בשנת {fiscal_year}".
- Pay ratio line if available: "יחס שכר מנכ"ל לעובד חציוני: {ceo_pay_ratio}:1 (עובד חציוני - {median_employee_total_comp_usd} דולר)".
- If ratio not disclosed: "החברה לא חשפה את היחס לעובד החציוני".
- Top 5 NEOs summary: list each as `{name} ({title}) - {total_comp_usd} דולר`.

## Rules

- Plain hyphen `-` only. No em dashes.
- Tickers always uppercase in filenames and JSON.
- ISO dates only. All money values integer USD, no formatting commas.
