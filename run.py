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
import diag
import halal
import macro

CHECK_LABELS = {
    "top_ranked": "Top 15% overall score",
    "uptrend": "Uptrend (above 50 & 200-day average)",
    "not_overbought": "Not overbought (RSI under 70)",
    "solid_fundamentals": "Solid fundamentals vs sector",
    "news_ok": "No negative company or competitor news",
    "macro_ok": "No strong sector or political headwind",
    "model_agrees": "Price model agrees",
}


def reasons(row):
    r = []
    from events import IMPACT, LABEL
    evs = row.get("events")
    for k in (evs if isinstance(evs, list) else [])[:2]:
        if abs(IMPACT[k]) >= 0.3:
            r.append(LABEL[k])
    if row["mom_12_1_r"] > 0.8: r.append("Strong 12m trend")
    if row["rel_str_63_r"] > 0.8: r.append("Beating index (3m)")
    if row["dist_ma200"] < -0.1 and row["ml"] > 0.7: r.append("Rebound setup")
    if row["rsi_14"] > 75: r.append("Overbought (RSI)")
    if row["value"] > 0.75: r.append("Cheap vs sector")
    if row["quality"] > 0.75: r.append("High quality")
    if row["growth"] > 0.75: r.append("Fast growth")
    if pd.notna(row.get("f_score")) and row["f_score"] >= 7: r.append("Strong financial health")
    if pd.notna(row.get("f_score")) and row["f_score"] <= 2: r.append("Weak financial health")
    if row["news_sent"] > 0.15: r.append("Positive news")
    if row["news_sent"] < -0.15: r.append("Negative news")
    if row["peer_sent"] > 0.1: r.append("Sector tailwind")
    if row["peer_sent"] < -0.1: r.append("Sector headwind")
    if row["macro_share"] > 0.4: r.append("Policy/macro in focus")
    if row["macro_raw"] >= 0.25: r.append("Macro tailwind")
    if row["macro_raw"] <= -0.25: r.append("Macro headwind")
    return r


def signal_checks(df, model_ok):
    return pd.DataFrame({
        "top_ranked": df["score"].rank(pct=True) >= 0.85,
        "uptrend": (df["dist_ma50"] > 0) & (df["dist_ma200"] > 0),
        "not_overbought": df["rsi_14"] < 70,
        "solid_fundamentals": df["fundamental"] >= 0.6,
        "news_ok": (df["news_sent"] >= 0) & (df["peer_sent"] >= -0.05),
        "macro_ok": (df["macro_raw"] >= -0.2) | (df["macro_raw"].rank(pct=True) >= 0.25),
        "model_agrees": (df["ml"] >= 0.7) if model_ok else pd.Series(True, index=df.index),
    })


MACRO_RED = -0.5   # sector/political score at or below this = red flag (AI events stack up, so keep it strict)
RED_FLAG_EVENTS = {"scandal", "guidance_down", "capital_raise", "bankruptcy", "debt", "ceo_exit",
                   "trial_fail", "rejection", "dividend_cut"}
SELL_LABELS = {
    "bottom_ranked": "Bottom 15% overall score",
    "downtrend": "Downtrend (below 50 & 200-day average)",
    "weak_fundamentals": "Weak fundamentals vs sector",
    "bad_news": "Negative company, competitor or sector news",
    "model_negative": "Price model is negative",
}


def sell_checks(df, model_ok):
    return pd.DataFrame({
        "bottom_ranked": df["score"].rank(pct=True) <= 0.15,
        "downtrend": (df["dist_ma50"] < 0) & (df["dist_ma200"] < 0),
        "weak_fundamentals": df["fundamental"] < 0.4,
        "bad_news": (df["news_sent"] < 0) | (df["peer_sent"] < -0.05) | ((df["macro_raw"] < -0.1) & (df["macro_raw"].rank(pct=True) <= 0.2)),
        "model_negative": (df["ml"] <= 0.3) if model_ok else pd.Series(True, index=df.index),
    })


def red_flags(df):
    """Recent serious bad news (event taxonomy) or a strong sector/political headwind."""
    out = {}
    mrank = df["macro_raw"].rank(pct=True)
    for t, r in df.iterrows():
        evs = r.get("events") if isinstance(r.get("events"), list) else []
        f = [__import__("events").LABEL[k] for k in evs if k in RED_FLAG_EVENTS]
        # A sector-wide/political headwind blocks BUY (see "macro_ok") and shows as a tag, but is not a
        # company red flag: it shouldn't by itself tell you to sell a company whose own picture is fine.
        if pd.notna(r["altman_z"]) and r["altman_z"] < 1.8 and pd.notna(r["f_score"]) and r["f_score"] <= 3:
            f.append("Financial distress risk")
        if pd.notna(r["interest_cover"]) and r["interest_cover"] < 1 and r["sector"] not in ("Financial Services", "Real Estate"):
            f.append("Profit doesn't cover interest")
        if pd.notna(r["dilution"]) and r["dilution"] > 0.2:
            f.append("Heavy share dilution")
        out[t] = f
    return pd.Series(out)


def labels(df, buy, sell, flags_red):
    """One label per stock, in priority order: SELL > AVOID (red flag) > BUY > WATCH > AVOID (weak) > HOLD."""
    nb, ns = buy.shape[1], sell.shape[1]
    lab = pd.Series("HOLD", index=df.index)
    weak = sell["bottom_ranked"] & sell["weak_fundamentals"]
    lab[weak] = "AVOID"
    lab[(buy.sum(axis=1) == nb - 1) & buy["top_ranked"]] = "WATCH"
    lab[buy.sum(axis=1) == nb] = "BUY"
    lab[flags_red.map(len) > 0] = "AVOID"
    lab[sell.sum(axis=1) == ns] = "SELL"
    return lab


SHORT_LABELS = {
    "momentum": "Strong short-term momentum (price model / 1-month move)",
    "catalyst": "Fresh positive news or event",
    "above_50d": "Above its 50-day average",
    "rsi_band": "RSI between 50 and 70 (rising, not overheated)",
    "interest": "Rising interest (volume or beating the index)",
    "no_red": "No red flags",
}
LONG_LABELS = {
    "fundamentals": "Top 30% fundamentals",
    "health": "Strong financial health (F-score 7+)",
    "not_distressed": "No bankruptcy risk (Altman Z safe or n/a)",
    "fair_value": "Not expensive vs its sector",
    "quality": "Top 30% quality (profitability, low debt)",
    "above_200d": "Above its 200-day average (long-term uptrend)",
    "no_headwind": "No structural sector/political headwind",
    "no_red": "No red flags",
}


def horizon_checks(df, model_ok, reds):
    """Short (days–weeks) and long (1 year+) BUY checklists. Medium = the main BUY checks."""
    good_event = df["events"].map(lambda e: any(__import__("events").IMPACT.get(k, 0) >= 0.3 for k in (e if isinstance(e, list) else [])))
    mom = (df["ml"] >= 0.8) if model_ok else ((df["ret_21_r"] >= 0.8) & (df["rel_str_63_r"] >= 0.6))
    short = pd.DataFrame({
        "momentum": mom,
        "catalyst": good_event | (df["news_sent"] > 0.15),
        "above_50d": df["dist_ma50"] > 0,
        "rsi_band": df["rsi_14"].between(50, 70),
        "interest": (df["vol_spike"] >= 1.2) | (df["rel_str_63_r"] >= 0.7),
        "no_red": reds.map(len) == 0,
    })
    f = df["f_score"]
    long = pd.DataFrame({
        "fundamentals": df["fundamental"].rank(pct=True) >= 0.7,
        "health": f >= 7,
        "not_distressed": df["altman_z"].isna() | (df["altman_z"] >= 3),
        "fair_value": df["value"] >= 0.5,
        "quality": df["quality"].rank(pct=True) >= 0.7,
        "above_200d": df["dist_ma200"] > 0,
        "no_headwind": (df["macro_raw"] >= -0.1) | (df["macro_raw"].rank(pct=True) >= 0.3),
        "no_red": reds.map(len) == 0,
    })
    return short, long


def horizon_label(checks, blocked):
    n = checks.shape[1]
    p = checks.sum(axis=1)
    out = pd.Series("", index=checks.index)
    out[p == n - 1] = "WATCH"
    out[p == n] = "BUY"
    out[blocked] = ""
    return out


def extra_flags(df, flags_red):
    """REBOUND: good company that's oversold. TAKE PROFIT: big run, overbought, support fading."""
    out = {}
    run_hi = df["ret_63"].quantile(0.9)
    for t, r in df.iterrows():
        f = []
        if r["rsi_14"] < 30 and r["fundamental"] >= 0.6 and not flags_red[t] and r["news_sent"] >= -0.05:
            f.append("REBOUND")
        if r["rsi_14"] > 75 and r["ret_63"] >= max(0.2, run_hi) and (r["ml"] < 0.5 or r["news_sent"] < 0):
            f.append("TAKE PROFIT")
        out[t] = f
    return pd.Series(out)


import time as _time


class Timer:
    """Records how long each stage of a market's run takes."""
    def __init__(self):
        self.t = {}
        self._last = _time.time()

    def lap(self, stage):
        now = _time.time()
        self.t[stage] = round(now - self._last, 1)
        self._last = now


def run_market(name, cfg, demo):
    diag.MARKET = name
    tm = Timer()
    kmi = None
    missing = []
    if demo:
        from demo_data import fake_market
        close, volume, idx, fund, news = fake_market(cfg["tickers"], cfg["index"])
        from demo_data import fake_health
        health = fake_health(cfg["tickers"])
    else:
        from data import get_fundamentals, get_index, get_news, get_prices
        from universe import get_universe
        uni = get_universe(name, cfg["tickers"])
        tm.lap("index list")
        close, volume = get_prices(list(uni.index), config.HISTORY)
        missing = [t for t in uni.index if t not in close.columns]
        # Use completed closes only: if this market is open right now, today's bar is a moving intraday price
        from zoneinfo import ZoneInfo
        tz, open_m, close_m = {"US": ("America/New_York", 570, 960), "ASX": ("Australia/Sydney", 600, 975),
                               "PSX": ("Asia/Karachi", 555, 960)}[name]
        now_l = datetime.now(ZoneInfo(tz))
        mins = now_l.hour * 60 + now_l.minute
        if (len(close) and close.index[-1].date() == now_l.date() and now_l.weekday() < 5
                and open_m <= mins < close_m + 30):
            print(f"[{name}] market is open ({now_l:%a %H:%M} local) — using the previous close, not intraday prices")
            diag.put("prices", intraday_bar_dropped=str(close.index[-1].date()))
            close, volume = close.iloc[:-1], volume.iloc[:-1]
        # An incomplete latest day (e.g. a market's data not fully in yet) would make most stocks look price-less
        dropped_days = []
        while len(close) > 300 and close.iloc[-1].notna().mean() < 0.6:
            dropped_days.append(str(close.index[-1].date()))
            close, volume = close.iloc[:-1], volume.iloc[:-1]
        if dropped_days:
            print(f"WARNING [{name}] latest day(s) {dropped_days} had prices for too few stocks — using {close.index[-1].date()}")
            diag.put("prices", incomplete_days_dropped=dropped_days)
        tm.lap("prices")
        if cfg["index_candidates"]:
            idx = get_index(cfg["index_candidates"], config.HISTORY).reindex(close.index).ffill()
        else:  # no index feed (Pakistan): equal-weighted index of the members' daily moves
            idx = (1 + close.pct_change().clip(-0.3, 0.3).mean(axis=1).fillna(0)).cumprod() * 100
        fund = get_fundamentals(list(close.columns), uni["name"].to_dict() if "name" in uni else None)
        tm.lap("fundamentals")
        diag.put("fundamentals", count=len(fund), **{
            f"missing_{k}": round(float(pd.to_numeric(fund[k], errors="coerce").isna().mean()), 2)
            for k in ("marketCap", "trailingPE", "profitMargins", "revenueGrowth", "returnOnEquity", "debtToEquity")
            if k in fund})
        fund["sector"] = fund["sector"].fillna(uni["sector"].reindex(fund.index))
        if name == "PSX" and "psx_sector" in fund:  # sector from the exchange's own company page
            from universe import psx_sector
            mapped = fund["psx_sector"].map(lambda x: psx_sector(x) if isinstance(x, str) else (None, None))
            fund["sector"] = [m[0] for m in mapped]
            fund["industry"] = [m[1] for m in mapped]
            unknown = fund["sector"].isna()
            if unknown.any():  # fall back to the index list's sector
                print(f"WARNING [PSX] sector not found on {int(unknown.sum())} company pages — using index list sector")
                diag.put("fundamentals", psx_sector_missing=int(unknown.sum()))
                for c in ("sector", "industry"):
                    if c in uni:
                        fund.loc[unknown, c] = uni[c].reindex(fund.index)[unknown]
        if "industry" in uni:
            fund["industry"] = fund["industry"].fillna(uni["industry"].reindex(fund.index))
        fund["shortName"] = fund["shortName"].fillna(uni["name"].reindex(fund.index))
        names = uni["name"].reindex(fund.index).fillna(fund["longName"]).fillna(fund["shortName"])
        news = get_news(list(close.columns), names.to_dict(), name)
        tm.lap("company news")
        from data import get_health
        if name == "PSX":
            health = fund[[c for c in ("f_score", "f_tests") if c in fund]].copy()
            from universe import kmi_members
            kmi = kmi_members()
        else:
            health = get_health(list(close.columns), pd.to_numeric(fund["marketCap"], errors="coerce").to_dict(),
                                fund["sector"].to_dict(), name)
        tm.lap("financial health")
    print(f"[{name}] {close.shape[1]} stocks, {len(close)} days")

    panel = technical_panel(close, volume, idx, config.HORIZON_DAYS)
    ml, stats = train_and_predict(panel, config.HORIZON_DAYS, config.TEST_DAYS)
    tm.lap("model")

    latest = panel.xs(panel.index.get_level_values("date").max(), level="date")
    ranks = latest[TECH_COLS].rank(pct=True).add_suffix("_r")
    fs = fundamental_score(fund, health)
    nf = news_features(news, fund["sector"])
    tm.lap("news scoring")

    hcols = [c for c in ("f_score", "f_tests", "altman_z", "interest_cover", "cash_conversion", "dilution", "margin_trend",
                         "total_debt", "cash", "interest_income", "revenue") if c in health]
    df = pd.concat([latest, ranks, fs, nf, health[hcols]], axis=1).reindex(ml.index)
    for c in ("f_score", "altman_z", "interest_cover", "cash_conversion", "dilution", "margin_trend",
              "total_debt", "cash", "interest_income", "revenue"):
        if c not in df:
            df[c] = np.nan
    df["ml"] = ml
    df["news"] = df["news_sent"].rank(pct=True).fillna(0.5)
    df["peers"] = df["peer_sent"].rank(pct=True).fillna(0.5)
    df["fundamental"] = df["fundamental"].fillna(0.5)
    for c in ["news_sent", "peer_sent", "macro_share"]:
        df[c] = df[c].fillna(0)

    # --- Screen: liquid, real companies only ---
    mcap = pd.to_numeric(fund["marketCap"], errors="coerce").reindex(df.index)
    price = close.ffill(limit=3).iloc[-1].reindex(df.index)
    ok = (df["dollar_vol"] >= cfg["min_dollar_vol"]) & (price >= 1) & ~(mcap < cfg["min_mcap"])
    diag.put("screen", total=int(len(df)), no_dollar_vol=int(df["dollar_vol"].isna().sum()),
             too_illiquid=int((df["dollar_vol"] < cfg["min_dollar_vol"]).sum()), no_price=int(price.isna().sum()),
             price_below_1=int((price < 1).sum()), too_small=int((mcap < cfg["min_mcap"]).sum()), passed=int(ok.sum()))
    if not ok.any():
        raise RuntimeError(f"no stocks passed the screen ({len(df)} checked: {int(price.isna().sum())} without today's price, "
                           f"{int((df['dollar_vol'] < cfg['min_dollar_vol']).sum())} too illiquid, "
                           f"{int((mcap < cfg['min_mcap']).sum())} too small)")
    df = df[ok].copy()
    # Drop duplicate tickers and rows with no usable price data (logged so we can see which)
    bad = df.index[df.index.duplicated() | df["dollar_vol"].isna() | price.reindex(df.index).isna()]
    if len(bad):
        print(f"WARNING [{name}] dropped {len(bad)} stocks with no usable price data: {', '.join(map(str, bad[:15]))}")
        diag.put("scoring", dropped_no_data=[str(t) for t in bad[:30]])
    df = df[~df.index.duplicated() & df["dollar_vol"].notna() & price.reindex(df.index).notna()].copy()

    # Sector news + political/macro themes
    df["sector"] = fund["sector"].reindex(df.index).fillna("Unknown")
    universe = {"sectors": sorted(df["sector"].dropna().unique()),
                "industries": sorted(fund["industry"].dropna().astype(str).unique()) if "industry" in fund else [],
                "tickers": list(df.index)}
    ctx = macro.macro_context(name, demo, universe)
    tm.lap("sector & politics")
    macro.apply(ctx, df, fund)
    df["macro"] = df["macro_raw"].rank(pct=True).fillna(0.5)

    # If the price model failed its backtest in this market, lean on the other parts
    model_ok = stats.get("ic_mean", 0) > config.MIN_MODEL_IC
    w = config.WEIGHTS if model_ok else config.WEIGHTS_NO_MODEL
    for k in config.WEIGHTS:  # a missing part counts as neutral rather than breaking the run
        n_missing = int(df[k].isna().sum())
        if n_missing:
            print(f"WARNING [{name}] {n_missing} stocks missing '{k}' score — set to neutral")
            diag.put("scoring", **{f"missing_{k}": n_missing})
        df[k] = df[k].fillna(0.5)
    df["score"] = sum(w[k] * df[k] for k in w) * 100
    df = df.sort_values("score", ascending=False)
    df["price"] = price.reindex(df.index)
    df["mcap"] = mcap.reindex(df.index)
    df["name"] = fund["shortName"].reindex(df.index)
    # Same company, two share classes (e.g. GOOG/GOOGL): keep the higher-scored one
    df = df[~(df["name"].notna() & df["name"].str.replace(r"\s*\(.*\)|\s+Class [A-Z].*", "", regex=True).duplicated())]
    df["sector"] = fund["sector"].reindex(df.index).fillna("Unknown")
    df["reasons"] = df.apply(reasons, axis=1)
    df["market"] = name
    # Shariah screen
    ind_s = fund["industry"].reindex(df.index) if "industry" in fund else pd.Series(None, index=df.index)
    hres = {t: halal.screen(t, name, r["sector"], ind_s.get(t), r["name"], r["mcap"], r["total_debt"], r["cash"],
                            r["interest_income"], r["revenue"], (t in kmi) if kmi is not None else None)
            for t, r in df.iterrows()}
    df["halal"] = pd.Series({t: v["status"] for t, v in hres.items()})
    df["halal_info"] = pd.Series(hres)
    diag.put("halal", **{k.lower().replace(" ", "_"): int(v) for k, v in df["halal"].value_counts().items()})
    checks = signal_checks(df, model_ok)
    schecks = sell_checks(df, model_ok)
    reds = red_flags(df)
    df["signal"] = labels(df, checks, schecks, reds)
    df["red_flags"] = reds
    df["flags"] = extra_flags(df, reds)
    hs, hl = horizon_checks(df, model_ok, reds)
    blocked = df["signal"].isin(["SELL", "AVOID"])
    df["hz_short"] = horizon_label(hs, blocked)
    df["hz_long"] = horizon_label(hl, blocked)
    stats.update(news_method=nf.attrs.get("method"), screened=int(ok.sum()),
                 news_coverage=round(float((df["news_count"].fillna(0) > 0).mean()), 2),
                 ai_scoring=("off" if not os.environ.get("ANTHROPIC_API_KEY")
                             else "on" if "claude" in (nf.attrs.get("method"), ctx.get("method")) or ctx.get("events")
                             else "failed"),
                 currency=cfg.get("currency", "USD" if name == "US" else "AUD"), index_name=cfg["index"],
                 price_date=str(close.index[-1].date()),
                 model_used=bool(model_ok), weights=w)
    stats.update(track_record(name, df, close, idx))
    try:
        stats["perf"] = performance(df, close, idx, fund)
    except Exception as e:
        print(f"[{name}] WARNING performance failed: {e}")
    stats["index_level"] = round(float(idx.dropna().iloc[-1]), 4)
    tm.lap("scoring & labels")
    stats["timings"] = tm.t
    stats["downloaded"] = int(close.shape[1])
    stats["missing_prices"] = missing

    stats["macro"] = {
        "method": ctx["method"],
        "sectors": {k: {kk: v[kk] for kk in ("score", "n", "why", "headlines")} for k, v in ctx["sectors"].items()},
        "themes": {k: {kk: v[kk] for kk in ("label", "heat", "n", "why", "headlines")} for k, v in ctx["themes"].items()},
        "events": ctx.get("events", []),
    }
    extras = {"close": close, "volume": volume, "idx": idx, "fund": fund, "checks": checks,
              "headlines": nf.attrs.get("headlines", {}), "weights": w, "model_ok": model_ok, "ctx": ctx,
              "schecks": schecks, "hshort": hs, "hlong": hl}
    return df, stats, extras


# ---------------------------------------------------------------- market & sector performance
PERIODS = [("1D", 1), ("1W", 5), ("1M", 21), ("3M", 63), ("YTD", None), ("1Y", 252), ("5Y", 1260)]


def _period_returns(px):
    """px: Series or DataFrame of closes. Returns {period: return} (Series per column for DataFrames)."""
    px = px.ffill()
    last = px.iloc[-1]
    out = {}
    for lab, n in PERIODS:
        if n is None:
            prev = px[px.index.year < px.index[-1].year]
            base = prev.iloc[-1] if len(prev) else None
        else:
            base = px.iloc[-n - 1] if len(px) > n else None
        out[lab] = None if base is None else last / base - 1
    return out


def performance(df, close, idx, fund):
    """Index returns plus market-cap-weighted sector and industry returns, within this market."""
    def clean(v):
        return None if v is None or not np.isfinite(v) else round(float(v), 4)
    ir = _period_returns(idx.dropna())
    res = {"index": {k: clean(v) for k, v in ir.items()}, "sectors": [], "industries": []}
    stock = _period_returns(close[df.index])
    w = df["mcap"].fillna(df["mcap"].median()).clip(lower=0)
    ind = fund["industry"].reindex(df.index) if "industry" in fund else pd.Series(None, index=df.index)
    for kind, key in (("sectors", df["sector"]), ("industries", ind)):
        for g, members in df.groupby(key):
            if kind == "industries" and len(members) < 3:
                continue
            m = members.index
            row = {"name": str(g), "n": int(len(m)), "ret": {},
                   "score": round(float(members["score"].mean()), 1),
                   "labels": {l: int((members["signal"] == l).sum()) for l in ("BUY", "WATCH", "AVOID", "SELL")}}
            for lab, _ in PERIODS:
                r = stock[lab]
                if r is None:
                    row["ret"][lab] = None
                    continue
                rr = r.reindex(m)
                ok = rr.notna()
                row["ret"][lab] = clean((rr[ok] * w[m][ok]).sum() / w[m][ok].sum()) if ok.sum() else None
            res[kind].append(row)
    res["sectors"].sort(key=lambda x: -(x["ret"]["1M"] or -9))
    res["industries"].sort(key=lambda x: -(x["ret"]["1M"] or -9))
    return res


SIGNAL_LOG = "results/signals.csv"


TRACKED = ("BUY", "SELL", "AVOID", "SHORT BUY", "LONG BUY")


def _label_mask(df, lab):
    if lab == "SHORT BUY":
        return df["hz_short"] == "BUY"
    if lab == "LONG BUY":
        return df["hz_long"] == "BUY"
    return df["signal"] == lab


def track_record(market, df, close, idx):
    """Log today's BUY / SELL / AVOID labels and score every past one against the index.
    A BUY 'wins' if it beat the index; a SELL or AVOID 'wins' if it lagged the index."""
    os.makedirs("results", exist_ok=True)
    cols = ["date", "market", "ticker", "price", "index_price", "label"]
    log = pd.read_csv(SIGNAL_LOG) if os.path.exists(SIGNAL_LOG) else pd.DataFrame(columns=cols)
    if "label" not in log:
        log["label"] = "BUY"
    log["label"] = log["label"].fillna("BUY")
    today = close.index[-1]
    last_px, last_idx = close.iloc[-1], float(idx.iloc[-1])

    past = log[log["market"] == market].copy()
    out = {"track_n": 0, "track": {}}
    recent = set()
    if len(past):
        past["days"] = [int((close.index > pd.Timestamp(d)).sum()) for d in past["date"]]
        past["ret"] = [last_px.get(t, np.nan) / p - 1 for t, p in zip(past["ticker"], past["price"])]
        past["excess"] = past["ret"] - (last_idx / past["index_price"] - 1)
        mature = past[(past["days"] >= 5) & past["excess"].notna()]
        for lab in TRACKED:
            m = mature[mature["label"] == lab]
            if len(m):
                win = (m["excess"] < 0) if lab in ("SELL", "AVOID") else (m["excess"] > 0)
                out["track"][lab] = {"n": int(len(m)), "avg_excess": round(float(m["excess"].mean()), 4),
                                     "win_rate": round(float(win.mean()), 2)}
        if "BUY" in out["track"]:  # keep the old fields for the BUY box
            b = out["track"]["BUY"]
            out.update(track_n=b["n"], track_avg_excess=b["avg_excess"], track_win_rate=b["win_rate"])
        out["track_open"] = int(len(past))
        recent = set(zip(past.loc[past["days"] < config.HORIZON_DAYS, "ticker"],
                         past.loc[past["days"] < config.HORIZON_DAYS, "label"]))

    new = [{"date": str(today.date()), "market": market, "ticker": t,
            "price": round(float(df.at[t, "price"]), 4), "index_price": round(last_idx, 4), "label": lab}
           for lab in TRACKED for t in df.index[_label_mask(df, lab)] if (t, lab) not in recent]
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


def _p100(v, what=""):
    """0..1 -> 0..100, treating a missing value as neutral (50) and logging it."""
    try:
        f = float(v)
        if np.isfinite(f):
            return round(f * 100)
    except (TypeError, ValueError):
        pass
    if what:
        print(f"WARNING missing value for {what} — shown as 50")
        diag.sample("scoring", "errors", f"missing {what}")
    return 50


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
                                           "news": "Company news", "peers": "Competitors' news",
                                           "macro": "Sector & politics"}[k],
                       "value": _p100(r[k], f"{t} {k}"), "weight": w[k]} for k in w],
            "sub": {k: (round(float(r[k]) * 100) if pd.notna(r[k]) else None) for k in ("value", "quality", "growth", "health")},
            "health": {"f_score": _num(r["f_score"], 1),
                       "f_tests": json.loads(r["f_tests"]) if isinstance(r.get("f_tests"), str) else {},
                       "altman_z": _num(r["altman_z"], 2), "interest_cover": _num(r["interest_cover"], 1),
                       "cash_conversion": _num(r["cash_conversion"], 2), "dilution": _num(r["dilution"], 3),
                       "margin_trend": _num(r["margin_trend"], 3), "financial": sec == "Financial Services"},
            "checks": [{"label": CHECK_LABELS[c], "pass": bool(ex["checks"].at[t, c]),
                        "skipped": c == "model_agrees" and not ex["model_ok"]}
                       for c in ex["checks"].columns],
            "reasons": r["reasons"],
            "sell_checks": [{"label": SELL_LABELS[c], "pass": bool(ex["schecks"].at[t, c]),
                             "skipped": c == "model_negative" and not ex["model_ok"]} for c in ex["schecks"].columns],
            "red_flags": r["red_flags"], "flags": r["flags"],
            "halal": dict(r["halal_info"], purification=halal.purification(r["halal_info"].get("ratios"))),
            "hz": {"short": r["hz_short"], "medium": r["signal"] if r["signal"] in ("BUY", "WATCH") else "", "long": r["hz_long"]},
            "short_checks": [{"label": SHORT_LABELS[c], "pass": bool(ex["hshort"].at[t, c])} for c in ex["hshort"].columns],
            "long_checks": [{"label": LONG_LABELS[c], "pass": bool(ex["hlong"].at[t, c])} for c in ex["hlong"].columns],
            "rsi": _num(r["rsi_14"], 1), "ret3m_raw": _num(r["ret_63"]),
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
            "events": [{"label": __import__("events").LABEL[k], "impact": __import__("events").IMPACT[k]}
                       for k in (r.get("events") if isinstance(r.get("events"), list) else [])],
            "news_avg": _num(r["news_sent"], 2), "peer_avg": _num(r["peer_sent"], 2),
            "macro_share": _num(r["macro_share"], 2),
            "macro": {"score": _num(r["macro_raw"], 2), "sector_news": _num(r["sector_news"], 2),
                      "effects": [{"theme": th, "effect": e} for th, e in (r["macro_effects"] if isinstance(r["macro_effects"], list) else [])],
                      "sector_why": ex["ctx"]["sectors"].get(sec, {}).get("why"),
                      "sector_headlines": ex["ctx"]["sectors"].get(sec, {}).get("headlines", [])[:4]},
            "peers": [{"ticker": p, "name": pr["name"], "score": _num(pr["score"], 1),
                       "ret3m": _num(pr["ret_63"]), "news": _num(pr["news_sent"], 2),
                       "pe": _num(pr["fwd_pe"], 1), "signal": pr["signal"]}
                      for p, pr in peers.iterrows()],
            "close": [_num(x, 3) for x in hist[t]],
        }
        with open(os.path.join(outdir, f"{t}.json"), "w") as f:
            json.dump(rec, f, separators=(",", ":"), default=str)


LOG_JSON = "results/runlog.json"
_LINES = []


def _tee_print():
    import builtins
    orig = builtins.print

    def p(*args, **kw):
        line = " ".join(str(x) for x in args)
        _LINES.append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {line}")
        orig(*args, **kw)
    builtins.print = p


def write_log(started, stats, fatal=None):
    """results/runlog.json keeps the last 60 runs; results/logs/ keeps full text logs for 30 runs."""
    os.makedirs("results/logs", exist_ok=True)
    finished = datetime.now(timezone.utc)
    warn = [l for l in _LINES if any(k in l for k in ("WARNING", "FAILED", "failed", "Traceback", "ERR", "no price data", "unavailable"))]
    entry = {
        "started": started.isoformat(timespec="seconds"), "finished": finished.isoformat(timespec="seconds"),
        "minutes": round((finished - started).total_seconds() / 60, 1),
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "manual"), "commit": os.environ.get("GITHUB_SHA", "")[:7],
        "status": "failed" if fatal or any(v.get("error") for v in stats.values()) else ("warnings" if warn else "ok"),
        "fatal": fatal, "warnings": warn[:40], "markets": {},
    }
    entry["checks"] = {m: diag.checks(m, v) for m, v in stats.items()}
    entry["errors"] = {m: diag.errors(m) for m in stats}
    entry["diag"] = diag.snapshot()
    worst = [c["status"] for cs in entry["checks"].values() for c in cs]
    if entry["status"] == "ok" and "FAIL" in worst:
        entry["status"] = "failed"
    elif entry["status"] == "ok" and "WARN" in worst:
        entry["status"] = "warnings"
    for m, v in stats.items():
        entry["markets"][m] = {k: v.get(k) for k in (
            "error", "downloaded", "screened", "news_coverage", "ai_scoring", "news_method", "price_date",
            "ic_mean", "model_used", "timings")}
        entry["markets"][m]["missing_prices"] = (v.get("missing_prices") or [])[:25]
        entry["markets"][m]["labels"] = v.get("label_counts")
        entry["markets"][m]["ai_events"] = len((v.get("macro") or {}).get("events", []))
    log = []
    if os.path.exists(LOG_JSON):
        try:
            log = json.load(open(LOG_JSON))
        except Exception:
            log = []
    log = ([entry] + log)[:60]
    json.dump(log, open(LOG_JSON, "w"), indent=1, default=str)
    name = finished.strftime("results/logs/%Y-%m-%d_%H%M.txt")
    open(name, "w").write("\n".join(_LINES))
    for old in sorted(glob.glob("results/logs/*.txt"))[:-30]:
        os.remove(old)
    os.makedirs("docs", exist_ok=True)
    slim = [{k: v for k, v in e.items() if k != "diag"} for e in log[:20]]
    json.dump(slim, open("docs/runlog.json", "w"), default=str)
    for m, cs in entry["checks"].items():
        for c in cs:
            print(f"CHECK [{m}] {c['status']:4} {c['stage']}: {c['msg']}" + (f"  → {c['hint']}" if c['hint'] else ""))
    print(f"Run {entry['status']} in {entry['minutes']} min")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    _tee_print()
    started = datetime.now(timezone.utc)
    stats = {}
    try:
        _main(a, stats)
    except Exception as e:
        import traceback
        traceback.print_exc()
        write_log(started, stats, fatal=f"{type(e).__name__}: {e}")
        raise
    write_log(started, stats)


def _main(a, stats):

    os.makedirs("results/history", exist_ok=True)
    os.makedirs("docs/stocks", exist_ok=True)
    for f in glob.glob("docs/stocks/*.json"):  # fresh detail files each run
        os.remove(f)

    tables = []
    for name, cfg in config.MARKETS.items():
        try:
            df, st, ex = run_market(name, cfg, a.demo)
            write_details(df, ex, name, "docs/stocks")
            st["label_counts"] = {k: int(v) for k, v in df["signal"].value_counts().items()}
            st["label_counts"].update({"SHORT BUY": int((df["hz_short"] == "BUY").sum()), "LONG BUY": int((df["hz_long"] == "BUY").sum())})
            tables.append(df); stats[name] = st
        except Exception as e:  # one market failing shouldn't kill the other
            import traceback; traceback.print_exc()
            print(f"[{name}] FAILED: {type(e).__name__}: {e}")
            stats[name] = {"error": f"{type(e).__name__}: {e}"}

    cols = ["market", "name", "sector", "price", "score", "ml", "fundamental", "news", "peers", "macro", "macro_raw",
            "mcap", "news_sent", "events", "value", "quality", "growth", "health", "f_score", "flags", "red_flags",
            "hz_short", "hz_long", "halal",
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
             "flags": r["flags"] if isinstance(r["flags"], list) else [],
             "hl": r["halal"],
             "hz": [r["hz_short"] or "", r["signal"] if r["signal"] in ("BUY", "WATCH") else "", r["hz_long"] or ""],
             "red": r["red_flags"] if isinstance(r["red_flags"], list) else [],
             "parts": {k: _p100(r[k], f"{t} {k}") for k in config.WEIGHTS},
             "pe": _num(r["fwd_pe"], 1),
             "ret3m": None if pd.isna(r["ret_63"]) else round(float(r["ret_63"]) * 100, 1),
             "rsi": _num(r["rsi_14"], 0), "mcap": _num(r["mcap"], 0),
             "ns": _num(r["news_sent"], 2), "ms": _num(r["macro_raw"], 2),
             "vq": [round(float(r[k]) * 100) if pd.notna(r[k]) else None for k in ("value", "quality", "growth", "health")],
             "f": _num(r["f_score"], 1),
             "events": [__import__("events").LABEL[k] for k in (r["events"] if isinstance(r["events"], list) else [])][:4],
             "reasons": r["reasons"]}
            for t, r in sub.iterrows()]
    with open("docs/data.json", "w") as f:
        json.dump(payload, f, separators=(",", ":"), default=str)
    write_page(payload, "docs/index.html")
    print(json.dumps(stats, indent=1, default=str))


if __name__ == "__main__":
    main()
