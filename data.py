"""Download prices, fundamentals and news from Yahoo Finance (free)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

FUND_FIELDS = [
    "shortName", "sector", "industry", "currency", "marketCap", "trailingPE",
    "forwardPE", "priceToBook", "profitMargins", "revenueGrowth", "earningsGrowth",
    "debtToEquity", "returnOnEquity", "freeCashflow",
]


def get_prices(tickers, period):
    """Return (close, volume) DataFrames: rows = dates, columns = tickers."""
    raw = yf.download(tickers, period=period, auto_adjust=True, group_by="ticker",
                      threads=True, progress=False)
    close, volume = {}, {}
    have = set(raw.columns.get_level_values(0)) if isinstance(raw.columns, pd.MultiIndex) else set()
    for t in tickers:
        if t in have:
            close[t] = raw[t]["Close"]
            volume[t] = raw[t]["Volume"]
    close = pd.DataFrame(close).dropna(how="all")
    volume = pd.DataFrame(volume).reindex(close.index)
    return close, volume


def _info(t):
    try:
        info = yf.Ticker(t).info or {}
    except Exception:
        info = {}
    row = {k: info.get(k) for k in FUND_FIELDS}
    row["ticker"] = t
    return row


def get_fundamentals(tickers):
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(_info, tickers))
    return pd.DataFrame(rows).set_index("ticker")


def _news(t):
    """Headlines from roughly the last 10 days."""
    out = []
    try:
        items = yf.Ticker(t).news or []
    except Exception:
        items = []
    now = datetime.now(timezone.utc)
    for it in items:
        c = it.get("content", it)  # yfinance changed format; handle both
        title = c.get("title")
        when = c.get("pubDate") or c.get("providerPublishTime")
        try:
            ts = (datetime.fromtimestamp(when, timezone.utc) if isinstance(when, (int, float))
                  else datetime.fromisoformat(str(when).replace("Z", "+00:00")))
        except Exception:
            ts = now
        if title and (now - ts).days <= 10:
            out.append(title)
    return t, out


def get_news(tickers):
    with ThreadPoolExecutor(8) as ex:
        return dict(ex.map(_news, tickers))
