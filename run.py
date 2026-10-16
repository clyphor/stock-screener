"""Daily run: screen -> score -> rank US and ASX stocks -> write results + phone page.

    python run.py          # real data from Yahoo Finance
    python run.py --demo   # fake data, to test the pipeline offline
"""
import argparse
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


def run_market(name, cfg, demo):
    tickers = cfg["tickers"]
    if demo:
        from demo_data import fake_market
        close, volume, idx, fund, news = fake_market(tickers, cfg["index"])
    else:
        from data import get_fundamentals, get_news, get_prices
        close, volume = get_prices(tickers + [cfg["index"]], config.HISTORY)
        idx = close.pop(cfg["index"]); volume = volume.drop(columns=cfg["index"], errors="ignore")
        fund = get_fundamentals(list(close.columns))
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
    df["name"] = fund["shortName"].reindex(df.index)
    df["sector"] = fund["sector"].reindex(df.index)
    df["reasons"] = df.apply(reasons, axis=1)
    df["market"] = name
    df["signal"] = signals(df, model_ok)
    stats["news_method"] = nf.attrs.get("method")
    stats["screened"] = int(ok.sum())
    stats["model_used"] = bool(model_ok)
    stats["weights"] = w
    stats.update(track_record(name, df, close, idx))
    return df, stats


def signals(df, model_ok):
    """BUY only when every independent check agrees; WATCH when all but one do."""
    checks = pd.DataFrame({
        "top_ranked": df["score"].rank(pct=True) >= 0.85,
        "uptrend": (df["dist_ma50"] > 0) & (df["dist_ma200"] > 0),
        "not_overbought": df["rsi_14"] < 70,
        "solid_fundamentals": df["fundamental"] >= 0.6,
        "news_ok": (df["news_sent"] >= 0) & (df["peer_sent"] >= -0.05),
        "model_agrees": (df["ml"] >= 0.7) if model_ok else True,
    })
    passed = checks.sum(axis=1)
    out = np.where(passed == checks.shape[1], "BUY",
                   np.where((passed == checks.shape[1] - 1) & checks["top_ranked"], "WATCH", ""))
    return pd.Series(out, index=df.index)


SIGNAL_LOG = "results/signals.csv"


def track_record(market, df, close, idx):
    """Log today's BUY signals and score every past one against the index."""
    os.makedirs("results", exist_ok=True)
    cols = ["date", "market", "ticker", "price", "index_price"]
    log = pd.read_csv(SIGNAL_LOG) if os.path.exists(SIGNAL_LOG) else pd.DataFrame(columns=cols)
    today = close.index[-1]
    last_px, last_idx = close.iloc[-1], float(idx.iloc[-1])

    # Score past signals for this market
    past = log[log["market"] == market].copy()
    out = {"track_n": 0}
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

    # Add today's new BUYs (skip tickers already signalled in the last ~month)
    recent = set(past.loc[past.get("days", pd.Series(dtype=int)) < config.HORIZON_DAYS, "ticker"]) if len(past) else set()
    new = [{"date": str(today.date()), "market": market, "ticker": t,
            "price": round(float(df.at[t, "price"]), 4), "index_price": round(last_idx, 4)}
           for t in df.index[df["signal"] == "BUY"] if t not in recent]
    if new:
        log = pd.concat([log, pd.DataFrame(new)], ignore_index=True)
        log.to_csv(SIGNAL_LOG, index=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()

    tables, stats = [], {}
    for name, cfg in config.MARKETS.items():
        try:
            df, st = run_market(name, cfg, a.demo)
            tables.append(df); stats[name] = st
        except Exception as e:  # one market failing shouldn't kill the other
            print(f"[{name}] FAILED: {e}")
            stats[name] = {"error": str(e)}

    os.makedirs("results/history", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    cols = ["market", "name", "sector", "price", "score", "ml", "fundamental", "news", "peers",
            "fwd_pe", "ret_63", "rsi_14", "news_count", "reasons", "signal"]
    allres = pd.concat(tables)[cols] if tables else pd.DataFrame(columns=cols)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    allres.to_csv("results/latest.csv", index_label="ticker")
    allres.to_csv(f"results/history/{today}.csv", index_label="ticker")

    payload = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
               "demo": a.demo, "stats": stats, "markets": {}}
    for name in config.MARKETS:
        sub = allres[allres["market"] == name].head(config.TOP_N)
        payload["markets"][name] = [
            {"ticker": t, "name": r["name"], "sector": r["sector"],
             "price": None if pd.isna(r["price"]) else round(float(r["price"]), 2),
             "score": round(float(r["score"]), 1), "signal": r["signal"],
             "parts": {k: round(float(r[k]) * 100) for k in config.WEIGHTS},
             "pe": None if pd.isna(r["fwd_pe"]) else round(float(r["fwd_pe"]), 1),
             "ret3m": None if pd.isna(r["ret_63"]) else round(float(r["ret_63"]) * 100, 1),
             "reasons": r["reasons"]}
            for t, r in sub.iterrows()]
    with open("docs/data.json", "w") as f:
        json.dump(payload, f, indent=1, default=str)
    write_page(payload, "docs/index.html")
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
