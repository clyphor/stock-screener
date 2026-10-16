"""Technical features (for the ML model) and fundamental scores."""
import numpy as np
import pandas as pd

TECH_COLS = ["ret_21", "ret_63", "mom_12_1", "rsi_14", "dist_ma50", "dist_ma200",
             "vol_21", "vol_spike", "rel_str_63", "drawdown_252"]


def _rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def technical_panel(close, volume, index_close, horizon):
    """Long table (date, ticker) with features and the forward target."""
    idx = index_close.reindex(close.index).ffill()
    f = {
        "ret_21": close.pct_change(21),
        "ret_63": close.pct_change(63),
        "mom_12_1": close.shift(21) / close.shift(252) - 1,
        "rsi_14": close.apply(_rsi),
        "dist_ma50": close / close.rolling(50).mean() - 1,
        "dist_ma200": close / close.rolling(200).mean() - 1,
        "vol_21": close.pct_change().rolling(21).std() * np.sqrt(252),
        "vol_spike": volume.rolling(5).mean() / volume.rolling(60).mean(),
        "rel_str_63": close.pct_change(63).sub(idx.pct_change(63), axis=0),
        "drawdown_252": close / close.rolling(252).max() - 1,
    }
    # Target: next-`horizon`-day return minus the index (excess return)
    fwd = close.shift(-horizon) / close - 1
    fwd_idx = idx.shift(-horizon) / idx - 1
    f["target"] = fwd.sub(fwd_idx, axis=0)
    f["dollar_vol"] = (close * volume).rolling(20).mean()

    panel = pd.concat({k: v.stack(future_stack=True) for k, v in f.items()}, axis=1)
    panel.index.names = ["date", "ticker"]
    return panel


def cs_rank(panel, cols):
    """Rank each feature within each date (0..1). Makes the model robust to regime shifts."""
    return panel.groupby(level="date")[cols].rank(pct=True)


def _pct(s, higher_is_better=True):
    r = s.rank(pct=True, ascending=higher_is_better)
    return r.fillna(0.5)


def health_score(h):
    """0..1 from Piotroski F-score, Altman Z zone, interest cover and share dilution (whatever is available)."""
    out = {}
    for t, r in h.iterrows():
        parts = []
        f = r.get("f_score")
        if pd.notna(f): parts.append((float(f) / 9, 0.5))
        z = r.get("altman_z")
        if pd.notna(z): parts.append((1.0 if z >= 3 else 0.5 if z >= 1.8 else 0.0, 0.2))
        ic = r.get("interest_cover")
        if pd.notna(ic): parts.append((1.0 if ic >= 5 else 0.5 if ic >= 1.5 else 0.0, 0.15))
        d = r.get("dilution")
        if pd.notna(d): parts.append((1.0 if d <= 0.02 else 0.5 if d <= 0.1 else 0.0, 0.15))
        out[t] = sum(v * w for v, w in parts) / sum(w for _, w in parts) if parts else np.nan
    return pd.Series(out, dtype=float)


def fundamental_score(fund, health=None):
    """Value + quality + growth + financial health, ranked within the market's universe (0..1)."""
    f = fund.copy()
    num = ["trailingPE", "forwardPE", "priceToBook", "profitMargins", "revenueGrowth",
           "earningsGrowth", "debtToEquity", "returnOnEquity", "freeCashflow", "marketCap"]
    for c in num:
        f[c] = pd.to_numeric(f[c], errors="coerce")
    pe = f["forwardPE"].where(f["forwardPE"] > 0, f["trailingPE"])
    earn_yield = 1 / pe.where(pe > 0)
    fcf_yield = f["freeCashflow"] / f["marketCap"]

    # Value relative to sector peers (a bank vs a bank, not a bank vs a chipmaker)
    sec = f["sector"].fillna("Unknown")
    value = pd.concat([earn_yield, fcf_yield], axis=1).groupby(sec).rank(pct=True).mean(axis=1)
    quality = pd.concat([_pct(f["returnOnEquity"]), _pct(f["profitMargins"]),
                         _pct(f["debtToEquity"], higher_is_better=False)], axis=1).mean(axis=1)
    growth = pd.concat([_pct(f["revenueGrowth"]), _pct(f["earningsGrowth"])], axis=1).mean(axis=1)

    out = pd.DataFrame({"value": value.fillna(0.5), "quality": quality, "growth": growth})
    hs = health_score(health).reindex(out.index) if health is not None else pd.Series(np.nan, index=out.index)
    out["health_raw"] = hs
    out["health"] = hs.rank(pct=True).fillna(0.5)
    out["fundamental"] = (0.30 * out["value"] + 0.25 * out["quality"] + 0.20 * out["growth"] + 0.25 * out["health"])
    out["fwd_pe"] = pe
    return out
