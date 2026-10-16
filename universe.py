"""Fetch the current S&P 500 and ASX 200 member lists (from Wikipedia).

Falls back to the last good list saved in results/, then to the short list in config.py.
"""
import io
import os
import urllib.request

import pandas as pd

SOURCES = {
    "US": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol", "GICS Sector", ""),
    "ASX": ("https://en.wikipedia.org/wiki/S%26P/ASX_200", "Code", "Sector", ".AX"),
}


def _fetch(market):
    url, col, sec_col, suffix = SOURCES[market]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (stock-screener)"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    for t in pd.read_html(io.StringIO(html)):
        if col in t.columns and len(t) >= 150:
            t = t.dropna(subset=[col])
            tick = t[col].astype(str).str.strip().str.replace(".", "-", regex=False) + suffix
            sec = t[sec_col] if sec_col in t.columns else pd.Series(None, index=t.index)
            return pd.Series(sec.values, index=tick.values, name="sector")
    raise ValueError("constituents table not found")


def get_universe(market, fallback):
    """Return Series ticker -> sector (sector may be None)."""
    cache = f"results/universe_{market}.csv"
    try:
        s = _fetch(market)
        os.makedirs("results", exist_ok=True)
        s.to_csv(cache, header=True)
        print(f"[{market}] universe: {len(s)} tickers from Wikipedia")
        return s
    except Exception as e:
        print(f"[{market}] could not fetch index list ({e}); using saved/fallback list")
    if os.path.exists(cache):
        return pd.read_csv(cache, index_col=0)["sector"]
    return pd.Series(None, index=fallback, name="sector", dtype=object)
