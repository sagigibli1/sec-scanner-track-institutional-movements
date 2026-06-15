"""Generate a fresh screener snapshot from 13F holdings + insider data."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "snapshots"

watchlist = json.loads((ROOT / "data" / "watchlist.json").read_text())
tickers   = watchlist["tickers"]
gurus     = watchlist["gurus"]

# Load latest holdings per guru
holdings = {}
for g in gurus:
    files = sorted(SNAPSHOTS.glob(f"holdings-{g['id']}-*.json"))
    if not files:
        continue
    data = json.loads(files[-1].read_text())
    holdings[g["id"]] = {p["ticker"]: p for p in data.get("positions", [])}

# Load diff files for new/increased positions
new_positions = {}  # ticker -> [guru_display]
for df in sorted(SNAPSHOTS.glob("diff-*.json")):
    d = json.loads(df.read_text())
    guru_id = d.get("guru", "")
    guru_display = next((g["display"] for g in gurus if g["id"] == guru_id), guru_id)
    for n in d.get("new", []):
        new_positions.setdefault(n["ticker"], []).append(guru_display)

# Load insider data
insider = {}
for t in tickers:
    p = SNAPSHOTS / f"insider-{t}.json"
    if p.exists():
        data = json.loads(p.read_text())
        trades = data.get("trades", [])
        insider[t] = {
            "buys_30d":  sum(1 for tr in trades if tr.get("action") == "buy"),
            "sells_30d": sum(1 for tr in trades if tr.get("action") == "sell"),
        }
    else:
        insider[t] = {"buys_30d": 0, "sells_30d": 0}

# Score each ticker
rankings = []
for t in tickers:
    score = 0.0
    top_buyers = []
    reasons = []

    holding_gurus = []
    for g in gurus:
        pos = holdings.get(g["id"], {}).get(t)
        if pos:
            holding_gurus.append(g["display"])
            score += 1.5

    new_by = new_positions.get(t, [])
    if new_by:
        score += 2.5 * len(new_by)
        top_buyers += new_by
        reasons.append(f"{', '.join(new_by)} opened new position this quarter")

    top_buyers += [g for g in holding_gurus if g not in top_buyers]

    ins = insider[t]
    score += min(ins["buys_30d"], 3)
    score -= min(ins["sells_30d"], 3) * 0.5
    score = round(min(max(score, 0), 10), 1)

    if new_by and holding_gurus:
        signal = "strong_buy"
    elif new_by or len(holding_gurus) >= 2:
        signal = "buy"
    elif holding_gurus:
        signal = "buy"
    else:
        signal = "hold"

    if not reasons:
        if holding_gurus:
            reasons.append(f"Held by {', '.join(holding_gurus[:2])}")
        else:
            reasons.append("No major guru position tracked this quarter")

    rankings.append({
        "ticker": t,
        "score": score,
        "signal": signal,
        "signal_reason": reasons[0],
        "top_buyers": top_buyers[:3],
        "insider_recent": ins,
    })

rankings.sort(key=lambda r: r["score"], reverse=True)

out = {
    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    "watchlist": tickers,
    "rankings": rankings,
}

for old in SNAPSHOTS.glob("screener-*.json"):
    old.unlink()

out_path = SNAPSHOTS / f"screener-{out['date']}.json"
out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(f"Written: {out_path.name}")
for r in rankings:
    print(f"  {r['ticker']:6s}  {r['score']:4.1f}  {r['signal']:12s}  {r['signal_reason']}")
