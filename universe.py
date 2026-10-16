"""Fetch the current S&P 500 and ASX 200 member lists (from Wikipedia).

Falls back to the last good list saved in results/, then to the short list in config.py.
"""
import io
import os
import urllib.request

import pandas as pd

SOURCES = {
    "US": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol", "GICS Sector", "", "Security"),
    "ASX": ("https://en.wikipedia.org/wiki/S%26P/ASX_200", "Code", "Sector", ".AX", "Company"),
}


def _fetch(market):
    url, col, sec_col, suffix, name_col = SOURCES[market]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (stock-screener)"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    for t in pd.read_html(io.StringIO(html)):
        if col in t.columns and len(t) >= 150:
            t = t.dropna(subset=[col])
            tick = t[col].astype(str).str.strip().str.replace(".", "-", regex=False) + suffix
            col_or_none = lambda c: t[c].values if c in t.columns else None
            return pd.DataFrame({"sector": col_or_none(sec_col), "name": col_or_none(name_col)},
                                index=pd.Index(tick.values, name="ticker"))
    raise ValueError("constituents table not found")


def get_universe(market, fallback):
    """Return DataFrame indexed by ticker with columns sector, name (may be empty)."""
    cache = f"results/universe_{market}.csv"
    try:
        s = _fetch(market)
        os.makedirs("results", exist_ok=True)
        s.to_csv(cache)
        print(f"[{market}] universe: {len(s)} tickers from Wikipedia")
        return s
    except Exception as e:
        print(f"[{market}] could not fetch index list ({e}); using saved/fallback list")
    if os.path.exists(cache):
        df = pd.read_csv(cache, index_col=0)
        if "name" not in df:
            df["name"] = None
        return df
    return pd.DataFrame({"sector": None, "name": None}, index=pd.Index(fallback, name="ticker"))
