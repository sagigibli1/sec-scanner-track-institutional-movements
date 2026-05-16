---
name: portfolio-diff
description: משווה שני רבעוני 13F של גורו ומחזיר diff עם פוזיציות חדשות, יציאות, הגדלות והקטנות
---

# /portfolio-diff {guru_id} {from_quarter} {to_quarter}

Compute a quarter-over-quarter diff for one guru. Output `diff-{guru}-{from_q}-{to_q}.json` per schema #3 in `SCHEMAS.md`.

## Arguments

- `$1` - guru ID (must appear in `data/watchlist.json`).
- `$2` - from quarter, format `YYYYQ[1-4]` (e.g. `2025Q4`).
- `$3` - to quarter, same format (e.g. `2026Q1`).

If any arg is missing or malformed, stop with a Hebrew usage line: "שימוש: /portfolio-diff berkshire_hathaway 2025Q4 2026Q1".

`$2` must be chronologically before `$3`. If not, swap them and warn the user.

## Steps

1. TodoWrite: "load both quarters", "compute diff", "validate", "write file".
2. For each of the two quarters, locate the holdings snapshot file `data/snapshots/holdings-{guru_id}-{quarter}.json`.
   - If a file is missing, do NOT fetch silently. Tell the user in Hebrew: "אין סנאפ לרבעון {quarter}. הרץ קודם: /flow-track {guru_id}". Stop.
   - This keeps every command self-contained and avoids burning EdgarTools quota inside a diff command.
3. Read both files. Build a dictionary keyed by `ticker` for each side.
4. Compute the diff:
   - `new`: tickers present in `to` and missing in `from`. Include `ticker`, `shares`, `value_usd`, `pct_of_portfolio`.
   - `exited`: tickers present in `from` and missing in `to`. Include `ticker`, `shares_sold = from.shares`, `value_usd = from.value_usd`.
   - `increased`: ticker in both, `to.shares > from.shares`. Include `ticker`, `old_shares`, `new_shares`, `delta_pct = (new-old)/old * 100` rounded to 1 decimal. Skip if `delta_pct < 1` to filter rounding noise.
   - `decreased`: ticker in both, `to.shares < from.shares`. Same fields. Skip if `abs(delta_pct) < 1`.
5. Compute `summary`:
   - `total_value_change_pct = (to.total_value_usd - from.total_value_usd) / from.total_value_usd * 100` rounded to 1 decimal.
   - Counts for each bucket.
6. `lag_days`: compute against the `to` quarter's `filing_date`. If `> 50`, add Hebrew warning in chat.
7. Validate the JSON. All four buckets must be arrays (possibly empty), not null.
8. Atomic write: `data/snapshots/diff-{guru_id}-{from_q}-{to_q}.json.tmp` then rename.

## Final chat message (Hebrew)

- Filename.
- One-line summary: "שינוי בשווי תיק: {total_value_change_pct}%, {new_positions_count} חדשות, {exited_positions_count} יציאות, {increased_positions_count} הגדלות, {decreased_positions_count} הקטנות".
- The 3 biggest new positions by `value_usd`.
- The 3 biggest exited positions by `value_usd`.
- If lag warning applies, repeat it.

## Error handling

- Missing snapshot file: see step 2.
- Identical quarters (`from == to`): stop with a Hebrew note "אותו רבעון משני הצדדים, אין מה להשוות".
- Empty positions on either side: still write the diff file (all buckets empty), tell the user in chat.

## Notes

- This command does NOT call EdgarTools or FMP. It is pure file-system work on existing snapshots. Cheap and offline.
