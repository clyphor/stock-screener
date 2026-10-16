"""Daily run: screen -> score -> rank US and ASX stocks -> write results + phone page.

    python run.py          # real data from Yahoo Finance
    python run.py --demo   # fake data, to test the pipeline offline
"""
import argparse
import glob
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config
from features import TECH_COLS, fundamental_score, technical_panel
from model import train_and_predict
from report import write_page
from sentiment import news_features

CHECK_LABELS = {
    "top_ranked": "Top 15% overall score",
    "uptrend": "Uptrend (above 50 & 200-day average)",
    "not_overbought": "Not overbought (RSI under 70)",
    "solid_fundamentals": "Solid fundamentals vs sector",
    "news_ok": "No negative company or sector news",
    "model_agrees": "Price model agrees",
}


def reasons(row):
    r = []
    if row["mom_12_1_r"] > 0.8: r.append("Strong 12m trend")
    if row["rel_str_63_r"] > 0.8: r.append("Beating index (3m)")
    if row["dist_ma200"] < -0.1 and row["ml"] > 0.7: r.append("Rebound setup")
    if row["rsi_14"] > 75: r.append("Overbought (RSI)")
    if row["value"] > 0.75: r.append("Cheap vs sector")
    if row["quality"] > 0.75: r.append("High quality")
    if row["growth"] > 0.75: r.append("Fast growth")
    if row["news_sent"] > 0.15: r.append("Positive news")
    if row["news_sent"] < -0.15: r.append("Negative news")
    if row["peer_sent"] > 0.1: r.append("Sector tailwind")
    if row["peer_sent"] < -0.1: r.append("Sector headwind")
    if row["macro_share"] > 0.4: r.append("Policy/macro in focus")
    return r


def signal_checks(df, model_ok):
    return pd.DataFrame({
        "top_ranked": df["score"].rank(pct=True) >= 0.85,
        "uptrend": (df["dist_ma50"] > 0) & (df["dist_ma200"] > 0),
        "not_overbought": df["rsi_14"] < 70,
        "solid_fundamentals": df["fundamental"] >= 0.6,
        "news_ok": (df["news_sent"] >= 0) & (df["peer_sent"] >= -0.05),
        "model_agrees": (df["ml"] >= 0.7) if model_ok else pd.Series(True, index=df.index),
    })


def signals(checks):
    """BUY only when every check passes; WATCH when all but one do (and it's top-ranked)."""
    passed = checks.sum(axis=1)
    n = checks.shape[1]
    out = np.where(passed == n, "BUY",
                   np.where((passed == n - 1) & checks["top_ranked"], "WATCH", ""))
    return pd.Series(out, index=checks.index)


def run_market(name, cfg, demo):
    if demo:
        from demo_data import fake_market
        close, volume, idx, fund, news = fake_market(cfg["tickers"], cfg["index"])
    else:
        from data import get_fundamentals, get_news, get_prices
        from universe import get_universe
        uni = get_universe(name, cfg["tickers"])
        tickers = list(uni.index)
        close, volume = get_prices(tickers + [cfg["index"]], config.HISTORY)
        idx = close.pop(cfg["index"]); volume = volume.drop(columns=cfg["index"], errors="ignore")
        fund = get_fundamentals(list(close.columns))
        fund["sector"] = fund["sector"].fillna(uni.reindex(fund.index))
        news = get_news(list(close.columns))
    print(f"[{name}] {close.shape[1]} stocks, {len(close)} days")

    panel = technical_panel(close, volume, idx, config.HORIZON_DAYS)
    ml, stats = train_and_predict(panel, config.HORIZON_DAYS, config.TEST_DAYS)

    latest = panel.xs(panel.index.get_level_values("date").max(), level="date")
    ranks = latest[TECH_COLS].rank(pct=True).add_suffix("_r")
    fs = fundamental_score(fund)
    nf = news_features(news, fund["sector"])

    df = pd.concat([latest, ranks, fs, nf], axis=1).reindex(ml.index)
    df["ml"] = ml
    df["news"] = df["news_sent"].rank(pct=True).fillna(0.5)
    df["peers"] = df["peer_sent"].rank(pct=True).fillna(0.5)
    df["fundamental"] = df["fundamental"].fillna(0.5)
    for c in ["news_sent", "peer_sent", "macro_share"]:
        df[c] = df[c].fillna(0)

    # --- Screen: liquid, real companies only ---
    mcap = pd.to_numeric(fund["marketCap"], errors="coerce").reindex(df.index)
    price = close.iloc[-1].reindex(df.index)
    ok = (df["dollar_vol"] >= cfg["min_dollar_vol"]) & (price >= 1) & ~(mcap < cfg["min_mcap"])
    df = df[ok].copy()

    # If the price model failed its backtest in this market, lean on the other parts
    model_ok = stats.get("ic_mean", 0) > config.MIN_MODEL_IC
    w = config.WEIGHTS if model_ok else config.WEIGHTS_NO_MODEL
    df["score"] = sum(w[k] * df[k] for k in w) * 100
    df = df.sort_values("score", ascending=False)
    df["price"] = price
    df["mcap"] = mcap
    df["name"] = fund["shortName"].reindex(df.index)
    df["sector"] = fund["sector"].reindex(df.index).fillna("Unknown")
    df["reasons"] = df.apply(reasons, axis=1)
    df["market"] = name
    checks = signal_checks(df, model_ok)
    df["signal"] = signals(checks)
    stats.update(news_method=nf.attrs.get("method"), screened=int(ok.sum()),
                 model_used=bool(model_ok), weights=w)
    stats.update(track_record(name, df, close, idx))

    extras = {"close": close, "volume": volume, "idx": idx, "fund": fund, "checks": checks,
              "headlines": nf.attrs.get("headlines", {}), "weights": w, "model_ok": model_ok}
    return df, stats, extras


SIGNAL_LOG = "results/signals.csv"


def track_record(market, df, close, idx):
    """Log today's BUY signals and score every past one against the index."""
    os.makedirs("results", exist_ok=True)
    cols = ["date", "market", "ticker", "price", "index_price"]
    log = pd.read_csv(SIGNAL_LOG) if os.path.exists(SIGNAL_LOG) else pd.DataFrame(columns=cols)
    today = close.index[-1]
    last_px, last_idx = close.iloc[-1], float(idx.iloc[-1])

    past = log[log["market"] == market].copy()
    out = {"track_n": 0}
    recent = set()
    if len(past):
        past["days"] = [int((close.index > pd.Timestamp(d)).sum()) for d in past["date"]]
        past["ret"] = [last_px.get(t, np.nan) / p - 1 for t, p in zip(past["ticker"], past["price"])]
        past["excess"] = past["ret"] - (last_idx / past["index_price"] - 1)
        mature = past[(past["days"] >= 5) & past["excess"].notna()]
        if len(mature):
            out = {"track_n": int(len(mature)),
                   "track_avg_excess": round(float(mature["excess"].mean()), 4),
                   "track_win_rate": round(float((mature["excess"] > 0).mean()), 2)}
        out["track_open"] = int(len(past))
        recent = set(past.loc[past["days"] < config.HORIZON_DAYS, "ticker"])

    new = [{"date": str(today.date()), "market": market, "ticker": t,
            "price": round(float(df.at[t, "price"]), 4), "index_price": round(last_idx, 4)}
           for t in df.index[df["signal"] == "BUY"] if t not in recent]
    if new:
        log = pd.concat([log, pd.DataFrame(new)], ignore_index=True)
        log.to_csv(SIGNAL_LOG, index=False)
    return out


# ---------------------------------------------------------------- detail pages
def _num(x, nd=4):
    try:
        x = float(x)
        return None if not np.isfinite(x) else round(x, nd)
    except (TypeError, ValueError):
        return None


FUND_ROWS = [  # (key, label, kind, higher_is_better)
    ("fwd_pe", "P/E (forward)", "x", False),
    ("priceToBook", "Price / book", "x", False),
    ("fcf_yield", "Free-cash-flow yield", "pct", True),
    ("profitMargins", "Profit margin", "pct", True),
    ("returnOnEquity", "Return on equity", "pct", True),
    ("revenueGrowth", "Revenue growth", "pct", True),
    ("earningsGrowth", "Earnings growth", "pct", True),
    ("debtToEquity", "Debt / equity", "x100", False),
    ("dividendYield", "Dividend yield", "dy", True),
]


def write_details(df, ex, market, outdir):
    """One small JSON per stock with everything the detail view needs."""
    fund = ex["fund"].copy()
    for c in [k for k, *_ in FUND_ROWS] + ["marketCap", "freeCashflow"]:
        if c in fund:
            fund[c] = pd.to_numeric(fund[c], errors="coerce")
    fund["fwd_pe"] = df["fwd_pe"]
    fund["fcf_yield"] = fund["freeCashflow"] / fund["marketCap"]
    fund["sector"] = df["sector"]
    med = fund.loc[df.index].groupby("sector")[[k for k, *_ in FUND_ROWS]].median()

    close, volume, idx = ex["close"], ex["volume"], ex["idx"]
    hist = close.iloc[-452:]  # 1y shown + 200 days to draw the 200-day average
    idx_h = idx.reindex(hist.index).ffill()
    dates = [d.strftime("%Y-%m-%d") for d in hist.index]
    w = ex["weights"]
    with open(os.path.join(outdir, f"_{market}.json"), "w") as f:  # shared by all stocks
        json.dump({"dates": dates, "index": [_num(x, 2) for x in idx_h]}, f, separators=(",", ":"))

    for t, r in df.iterrows():
        sec = r["sector"]
        peers = df[(df["sector"] == sec) & (df.index != t)].sort_values("mcap", ascending=False).head(6)
        rec = {
            "ticker": t, "name": r["name"], "sector": sec, "market": market,
            "industry": fund.at[t, "industry"] if "industry" in fund else None,
            "price": _num(r["price"], 2), "mcap": _num(r["mcap"], 0), "signal": r["signal"],
            "score": _num(r["score"], 1),
            "rank": int(df.index.get_loc(t)) + 1, "of": int(len(df)),
            "parts": [{"key": k, "label": {"ml": "Price model", "fundamental": "Fundamentals",
                                           "news": "Company news", "peers": "Peers / sector news"}[k],
                       "value": round(float(r[k]) * 100), "weight": w[k]} for k in w],
            "sub": {"value": round(float(r["value"]) * 100), "quality": round(float(r["quality"]) * 100),
                    "growth": round(float(r["growth"]) * 100)},
            "checks": [{"label": CHECK_LABELS[c], "pass": bool(ex["checks"].at[t, c]),
                        "skipped": c == "model_agrees" and not ex["model_ok"]}
                       for c in ex["checks"].columns],
            "reasons": r["reasons"],
            "tech": {
                "RSI (14 day)": _num(r["rsi_14"], 1),
                "1-month return": _num(r["ret_21"]), "3-month return": _num(r["ret_63"]),
                "12-month momentum": _num(r["mom_12_1"]),
                "vs 50-day average": _num(r["dist_ma50"]), "vs 200-day average": _num(r["dist_ma200"]),
                "3m return vs index": _num(r["rel_str_63"]),
                "Off 52-week high": _num(r["drawdown_252"]),
                "Volatility (annual)": _num(r["vol_21"]),
                "Volume vs normal": _num(r["vol_spike"], 2),
            },
            "fund": [{"label": lab, "kind": kind, "better": "high" if hib else "low",
                      "value": _num(fund.at[t, k]) if k in fund else None,
                      "sector": _num(med.at[sec, k]) if sec in med.index else None}
                     for k, lab, kind, hib in FUND_ROWS],
            "analyst": {"rating": fund.at[t, "recommendationKey"] if "recommendationKey" in fund else None,
                        "target": _num(fund.at[t, "targetMeanPrice"], 2) if "targetMeanPrice" in fund else None},
            "news": ex["headlines"].get(t, [])[:12],
            "news_avg": _num(r["news_sent"], 2), "peer_avg": _num(r["peer_sent"], 2),
            "macro_share": _num(r["macro_share"], 2),
            "peers": [{"ticker": p, "name": pr["name"], "score": _num(pr["score"], 1),
                       "ret3m": _num(pr["ret_63"]), "news": _num(pr["news_sent"], 2),
                       "pe": _num(pr["fwd_pe"], 1), "signal": pr["signal"]}
                      for p, pr in peers.iterrows()],
            "close": [_num(x, 3) for x in hist[t]],
        }
        with open(os.path.join(outdir, f"{t}.json"), "w") as f:
            json.dump(rec, f, separators=(",", ":"), default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()

    os.makedirs("results/history", exist_ok=True)
    os.makedirs("docs/stocks", exist_ok=True)
    for f in glob.glob("docs/stocks/*.json"):  # fresh detail files each run
        os.remove(f)

    tables, stats = [], {}
    for name, cfg in config.MARKETS.items():
        try:
            df, st, ex = run_market(name, cfg, a.demo)
            write_details(df, ex, name, "docs/stocks")
            tables.append(df); stats[name] = st
        except Exception as e:  # one market failing shouldn't kill the other
            import traceback; traceback.print_exc()
            stats[name] = {"error": str(e)}

    cols = ["market", "name", "sector", "price", "score", "ml", "fundamental", "news", "peers",
            "fwd_pe", "ret_63", "rsi_14", "news_count", "reasons", "signal"]
    allres = pd.concat(tables)[cols] if tables else pd.DataFrame(columns=cols)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    allres.to_csv("results/latest.csv", index_label="ticker")
    allres.to_csv(f"results/history/{today}.csv", index_label="ticker")

    payload = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
               "demo": a.demo, "stats": stats, "top_n": config.TOP_N, "markets": {}}
    for name in config.MARKETS:
        sub = allres[allres["market"] == name]
        payload["markets"][name] = [
            {"ticker": t, "name": r["name"], "sector": r["sector"],
             "price": _num(r["price"], 2), "score": _num(r["score"], 1), "signal": r["signal"],
             "parts": {k: round(float(r[k]) * 100) for k in config.WEIGHTS},
             "pe": _num(r["fwd_pe"], 1),
             "ret3m": None if pd.isna(r["ret_63"]) else round(float(r["ret_63"]) * 100, 1),
             "reasons": r["reasons"]}
            for t, r in sub.iterrows()]
    with open("docs/data.json", "w") as f:
        json.dump(payload, f, separators=(",", ":"), default=str)
    write_page(payload, "docs/index.html")
    print(json.dumps(stats, indent=1, default=str))


if __name__ == "__main__":
    main()
