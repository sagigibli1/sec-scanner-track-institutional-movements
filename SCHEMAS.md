# Shared JSON Schemas

All workflow outputs write to `data/snapshots/`. All renderers read from `data/snapshots/`. This is the contract.

## 1. `holdings-{guru}-{quarter}.json` - 13F holdings snapshot

```json
{
  "guru": "berkshire_hathaway",
  "guru_display": "Berkshire Hathaway",
  "quarter": "2026Q1",
  "filing_date": "2026-05-15",
  "source": "edgartools|fmp",
  "total_value_usd": 287400000000,
  "positions": [
    {
      "ticker": "AAPL",
      "company": "Apple Inc",
      "shares": 905560000,
      "value_usd": 174300000000,
      "pct_of_portfolio": 60.6,
      "change_pct": -0.3
    }
  ]
}
```

## 2. `insider-{ticker}.json` - Form 4 insider trades

```json
{
  "ticker": "TSLA",
  "company": "Tesla Inc",
  "as_of": "2026-05-17",
  "trades": [
    {
      "date": "2026-05-14",
      "insider": "Elon Musk",
      "role": "CEO",
      "action": "buy|sell",
      "shares": 100000,
      "price_usd": 320.5,
      "value_usd": 32050000,
      "transaction_code": "P|S|A|M",
      "form_url": "https://www.sec.gov/..."
    }
  ]
}
```

## 3. `diff-{guru}-{from_q}-{to_q}.json` - Quarter-over-quarter portfolio diff

```json
{
  "guru": "berkshire_hathaway",
  "from_quarter": "2025Q4",
  "to_quarter": "2026Q1",
  "summary": {
    "total_value_change_pct": 4.2,
    "new_positions_count": 2,
    "exited_positions_count": 1,
    "increased_positions_count": 5,
    "decreased_positions_count": 3
  },
  "new": [
    {
      "ticker": "NVDA",
      "shares": 2000000,
      "value_usd": 1800000000,
      "pct_of_portfolio": 0.6
    }
  ],
  "exited": [
    { "ticker": "HPQ", "shares_sold": 10000000, "value_usd": 320000000 }
  ],
  "increased": [
    {
      "ticker": "OXY",
      "old_shares": 248000000,
      "new_shares": 260000000,
      "delta_pct": 4.8
    }
  ],
  "decreased": [
    {
      "ticker": "BAC",
      "old_shares": 1000000000,
      "new_shares": 940000000,
      "delta_pct": -6.0
    }
  ]
}
```

## 4. `screener-{date}.json` - Daily screener output

```json
{
  "date": "2026-05-17",
  "watchlist": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOG"],
  "rankings": [
    {
      "ticker": "NVDA",
      "score": 8.5,
      "signal": "strong_buy|buy|hold|sell|strong_sell",
      "signal_reason": "5 superinvestors added positions this quarter",
      "top_buyers": ["Ackman", "Burry"],
      "insider_recent": { "buys_30d": 2, "sells_30d": 0 }
    }
  ]
}
```

## 5. `newsletter-{week}.json` - Weekly newsletter input

```json
{
  "week_start": "2026-05-11",
  "week_end": "2026-05-17",
  "highlights": [
    {
      "type": "insider_buy|insider_sell|13f_new|13f_exit|13d_filing",
      "headline_he": "באפט הוסיף 2 מיליארד דולר ל-NVDA",
      "ticker": "NVDA",
      "guru_or_insider": "Berkshire Hathaway",
      "value_usd": 2000000000,
      "context_he": "רבעון ראשון שהוא קונה את המניה"
    }
  ]
}
```

## Watchlist format - `data/watchlist.json`

```json
{
  "tickers": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOG", "AMZN", "META"],
  "gurus": [
    {
      "id": "berkshire_hathaway",
      "cik": "0001067983",
      "display": "Berkshire Hathaway"
    },
    { "id": "michael_burry", "cik": "0001649339", "display": "Michael Burry" },
    {
      "id": "bill_ackman",
      "cik": "0001336528",
      "display": "Bill Ackman / Pershing"
    }
  ],
  "insider_watch": ["TSLA", "NVDA", "META"]
}
```

## Rules

- All dates in ISO 8601 (`YYYY-MM-DD`)
- All quarters in `YYYY[Q1|Q2|Q3|Q4]` format
- All money values in USD, no formatting (integers preferred)
- All Hebrew strings UTF-8, RTL-safe (no embedded LTR English without bidi marks if needed for rendering)
- File names lowercase, snake_case for guru IDs
- Atomic writes (write to `.tmp` then rename)
