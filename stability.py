"""Label stability: labels have memory, so they only change for a real, recorded reason.

Rules (applied to the main signal and to the short/long-term horizon labels):
- Same price date as last time (a re-run on the same data): keep yesterday's decision. Only a NEW company
  red flag can change it (that's news, not noise).
- New trading day:
  * Upgrades (e.g. WATCH -> BUY) happen straight away.
  * Company red flags (AVOID/SELL) happen straight away.
  * Other downgrades (e.g. BUY -> WATCH/HOLD) need TWO trading days in a row of failing; on day one the
    label is kept and the stock is tagged "Weakening".
- When the scoring rules change (SCORING_VERSION in config.py), changes are recorded as "rules updated"
  so you can tell a rules change from a market change.
Every change is written to results/label_history.csv and shown on the stock page.
"""
import os
from datetime import datetime, timezone

import pandas as pd

STATE = "results/label_state.csv"
HISTORY = "results/label_history.csv"
RANK = {"BUY": 4, "WATCH": 3, "HOLD": 2, "": 2, "AVOID": 0, "SELL": 0}
FIELDS = {"signal": "Main", "hz_short": "Short-term", "hz_long": "Long-term"}


def _norm(v):
    return "" if v is None or (isinstance(v, float) and v != v) else str(v)


def apply(market, df, price_date, version):
    """Edits df in place (signal, hz_short, hz_long), adds 'weakening' and returns nothing."""
    state = pd.read_csv(STATE, dtype=str).fillna("") if os.path.exists(STATE) else pd.DataFrame(
        columns=["market", "ticker", "field", "label", "price_date", "down_days", "version", "since"])
    hist_rows = []
    st = state[state["market"] == market].set_index(["ticker", "field"])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    df["weakening"] = False
    new_state = []
    for t, r in df.iterrows():
        has_red = bool(r.get("red_flags")) if isinstance(r.get("red_flags"), list) else False
        for f, fname in FIELDS.items():
            new = _norm(r[f]) if f != "signal" else (_norm(r[f]) if r[f] not in ("HOLD",) else "")
            key = (t, f)
            if key not in st.index:
                final, down, since = new, 0, now
                if new:
                    hist_rows.append([now, market, t, fname, "(new)", new, "first seen", price_date])
            else:
                p = st.loc[key]
                prev, prev_date, down = p["label"], p["price_date"], int(p["down_days"] or 0)
                since = p["since"] or now
                rules_changed = p["version"] != str(version)
                same_day = prev_date == price_date
                if new == prev:
                    final, down = new, 0
                elif new in ("AVOID", "SELL") and has_red:            # real company bad news: act now
                    final, down = new, 0
                elif same_day and not rules_changed:                   # re-run on identical data: keep
                    final = prev
                elif RANK.get(new, 2) > RANK.get(prev, 2):             # upgrade: act now
                    final, down = new, 0
                elif prev in ("AVOID", "SELL") and not has_red:        # red flag cleared
                    final, down = new, 0
                else:                                                  # downgrade: needs 2 days in a row
                    down = down + (0 if same_day else 1)
                    if down >= 2:
                        final, down = new, 0
                    else:
                        final = prev
                        if f == "signal" or prev == "BUY":
                            df.at[t, "weakening"] = True
                if final != prev:
                    why = ("rules updated" if rules_changed else
                           "company red flag: " + ", ".join(r["red_flags"]) if final in ("AVOID", "SELL") and has_red else
                           "red flag cleared" if prev in ("AVOID", "SELL") else
                           "passed all checks" if RANK.get(final, 2) > RANK.get(prev, 2) else
                           "failed checks 2 trading days in a row")
                    hist_rows.append([now, market, t, fname, prev or "–", final or "–", why, price_date])
                    since = now
            df.at[t, f] = final if f != "signal" else (final or "HOLD")
            new_state.append([market, t, f, final, price_date, down, str(version), since])

    keep = state[state["market"] != market]
    out = pd.concat([keep, pd.DataFrame(new_state, columns=state.columns)], ignore_index=True)
    os.makedirs("results", exist_ok=True)
    out.to_csv(STATE, index=False)
    if hist_rows:
        h = pd.DataFrame(hist_rows, columns=["when", "market", "ticker", "field", "from", "to", "why", "price_date"])
        h.to_csv(HISTORY, mode="a", header=not os.path.exists(HISTORY), index=False)


def history(market, ticker, n=12):
    if not os.path.exists(HISTORY):
        return []
    h = pd.read_csv(HISTORY, dtype=str).fillna("")
    h = h[(h["market"] == market) & (h["ticker"] == ticker) & (h["from"] != "(new)")]
    return h.tail(n).iloc[::-1][["when", "field", "from", "to", "why", "price_date"]].to_dict("records")
