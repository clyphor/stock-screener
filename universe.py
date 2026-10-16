"""Fetch the current S&P 500 and ASX 200 member lists (from Wikipedia).

Falls back to the last good list saved in results/, then to the short list in config.py.
"""
import html as html_lib
import io
import re
import os
import urllib.request

import pandas as pd

import diag

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


PSX_SECTORS = [  # (PSX sector keyword, Yahoo-style sector, industry used by the theme maps)
    ("investment", "Financial Services", "Capital Markets"), ("modaraba", "Financial Services", "Capital Markets"),
    ("bank", "Financial Services", "Banks - Regional"), ("insurance", "Financial Services", "Insurance - Diversified"), ("leasing", "Financial Services", "Credit Services"),
    ("exploration", "Energy", "Oil & Gas E&P"), ("oil & gas marketing", "Energy", "Oil & Gas Refining & Marketing"),
    ("refinery", "Energy", "Oil & Gas Refining & Marketing"), ("cement", "Basic Materials", "Building Materials"),
    ("fertilizer", "Basic Materials", "Agricultural Inputs"), ("chemical", "Basic Materials", "Chemicals"),
    ("power", "Utilities", "Utilities - Independent Power Producers"), ("pharma", "Healthcare", "Drug Manufacturers - Specialty & Generic"),
    ("technology", "Technology", "Information Technology Services"), ("automobile", "Consumer Cyclical", "Auto Manufacturers"),
    ("auto parts", "Consumer Cyclical", "Auto Parts"), ("textile", "Consumer Cyclical", "Textile Manufacturing"),
    ("food", "Consumer Defensive", "Packaged Foods"), ("tobacco", "Consumer Defensive", "Tobacco"),
    ("engineering", "Industrials", "Steel"), ("glass", "Industrials", "Building Products & Equipment"),
    ("paper", "Basic Materials", "Paper & Paper Products"), ("transport", "Industrials", "Marine Shipping"),
    ("cable", "Industrials", "Electrical Equipment & Parts"), ("property", "Real Estate", "Real Estate - Development"),
    ("real estate", "Real Estate", "REIT - Diversified"), ("communication", "Communication Services", "Telecom Services"),
    ("holding", "Industrials", "Conglomerates"), ("miscellaneous", "Industrials", "Conglomerates"),
]


def psx_sector(name):
    n = str(name or "").lower()
    for kw, sec, ind in PSX_SECTORS:
        if kw in n:
            return sec, ind
    return "Industrials", "Conglomerates"


def _fetch_psx():
    req = urllib.request.Request("https://dps.psx.com.pk/indices/KSE100", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    rows = re.findall(r'href="/company/([A-Z0-9]+)"[^>]*data-title="([^"]*)"', html)
    if len(rows) < 80:
        raise ValueError(f"only {len(rows)} KSE-100 members found")
    sec = {}
    try:  # PSX sectors from Wikipedia's KSE-100 table
        req = urllib.request.Request("https://en.wikipedia.org/wiki/KSE_100_Index", headers={"User-Agent": "Mozilla/5.0 (stock-screener)"})
        for t in pd.read_html(io.StringIO(urllib.request.urlopen(req, timeout=30).read().decode())):
            if "Ticker" in t.columns and len(t) > 50:
                scol = [c for c in t.columns if "sector" in str(c).lower()][0]
                sec = dict(zip(t["Ticker"].astype(str).str.strip(), t[scol]))
    except Exception as e:
        print("[PSX] sector list unavailable:", e)
    df = pd.DataFrame({"name": [html_lib.unescape(n) for _, n in rows], "psx_sector": [sec.get(s) for s, _ in rows]},
                      index=pd.Index([s + ".KA" for s, _ in rows], name="ticker"))
    df = df[~df.index.duplicated()]
    df["sector"] = [psx_sector(x)[0] for x in df["psx_sector"]]
    df["industry"] = [psx_sector(x)[1] for x in df["psx_sector"]]
    return df


def kmi_members():
    """Symbols in PSX's KMI All-Share Islamic Index (Shariah-compliant), or None if unavailable."""
    cache = "results/kmi_allshare.csv"
    try:
        req = urllib.request.Request("https://dps.psx.com.pk/indices/KMIALLSHR", headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=30).read().decode()
        syms = sorted(set(re.findall(r'href="/company/([A-Z0-9]+)"', html)))
        if len(syms) < 100:
            raise ValueError(f"only {len(syms)} members found")
        os.makedirs("results", exist_ok=True)
        pd.Series(syms, name="symbol").to_csv(cache, index=False)
        diag.put("halal", kmi_source="live", kmi_count=len(syms))
        return set(s + ".KA" for s in syms)
    except Exception as e:
        print(f"WARNING [PSX] KMI Islamic index list unavailable ({e})")
        diag.sample("halal", "errors", f"KMI list: {e}")
        if os.path.exists(cache):
            syms = pd.read_csv(cache)["symbol"].astype(str)
            diag.put("halal", kmi_source="saved list", kmi_count=len(syms))
            return set(s + ".KA" for s in syms)
    return None


def get_universe(market, fallback):
    """Return DataFrame indexed by ticker with columns sector, name (may be empty)."""
    cache = f"results/universe_{market}.csv"
    try:
        s = _fetch_psx() if market == "PSX" else _fetch(market)
        os.makedirs("results", exist_ok=True)
        s.to_csv(cache)
        print(f"[{market}] universe: {len(s)} tickers from Wikipedia")
        diag.put("universe", source="live", count=len(s))
        return s
    except Exception as e:
        print(f"WARNING [{market}] could not fetch index list ({e}); using saved/fallback list")
        diag.sample("universe", "errors", str(e))
    if os.path.exists(cache):
        df = pd.read_csv(cache, index_col=0)
        diag.put("universe", source="saved list", count=len(df))
        if "name" not in df:
            df["name"] = None
        return df
    diag.put("universe", source="built-in fallback", count=len(fallback))
    return pd.DataFrame({"sector": None, "name": None}, index=pd.Index(fallback, name="ticker"))
