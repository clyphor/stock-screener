"""Stocks users asked the screener to analyse (on-demand), read from the database.

Only tickers are read — never who asked (see the requested_tickers() function in the database).
"""
import json
import os
import urllib.request

import config
import diag

CACHE = "cache"


def requested():
    """[{ticker, market}] from the database, or [] if unavailable."""
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        return []
    req = urllib.request.Request(config.SUPABASE_URL + "/rest/v1/rpc/requested_tickers", data=b"{}", method="POST",
                                 headers={"apikey": config.SUPABASE_ANON_KEY, "Content-Type": "application/json"})
    try:
        rows = json.loads(urllib.request.urlopen(req, timeout=30).read())
        diag.put("tracked", count=len(rows), market="general")
        return [{"ticker": r["ticker"], "market": r["market"]} for r in rows]
    except Exception as e:
        print("WARNING could not read requested stocks from the database:", e)
        diag.sample("tracked", "errors", str(e), market="general")
        return []


def by_market(rows):
    out = {}
    for r in rows:
        out.setdefault(r["market"], []).append(r["ticker"])
    return out


# ---- per-market cache written by the daily run, reused by on-demand runs (no repeat AI cost) ----
def save_cache(market, fund, news_scored, ctx, price_date, universe):
    d = os.path.join(CACHE, market)
    os.makedirs(d, exist_ok=True)
    fund.to_csv(os.path.join(d, "fund.csv"), index_label="ticker")
    with open(os.path.join(d, "news.json"), "w") as f:
        json.dump(news_scored, f, default=str)
    with open(os.path.join(d, "ctx.json"), "w") as f:
        json.dump(ctx, f, default=str)
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump({"price_date": price_date, "universe": list(universe)}, f)


def load_cache(market):
    import pandas as pd
    d = os.path.join(CACHE, market)
    if not os.path.exists(os.path.join(d, "meta.json")):
        return None
    with open(os.path.join(d, "meta.json")) as f:
        meta = json.load(f)
    with open(os.path.join(d, "news.json")) as f:
        news = json.load(f)
    with open(os.path.join(d, "ctx.json")) as f:
        ctx = json.load(f)
    fund = pd.read_csv(os.path.join(d, "fund.csv"), index_col="ticker")
    return {"meta": meta, "news": news, "ctx": ctx, "fund": fund}
