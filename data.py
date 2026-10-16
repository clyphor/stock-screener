"""Download prices, fundamentals and news from Yahoo Finance (free)."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

FUND_FIELDS = [
    "shortName", "sector", "industry", "currency", "marketCap", "trailingPE",
    "forwardPE", "priceToBook", "profitMargins", "revenueGrowth", "earningsGrowth",
    "debtToEquity", "returnOnEquity", "freeCashflow", "dividendYield",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "recommendationKey", "targetMeanPrice",
]


def get_prices(tickers, period):
    """Return (close, volume) DataFrames: rows = dates, columns = tickers."""
    raw = yf.download(tickers, period=period, auto_adjust=True, group_by="ticker",
                      threads=True, progress=False)
    close, volume = {}, {}
    have = set(raw.columns.get_level_values(0)) if isinstance(raw.columns, pd.MultiIndex) else set()
    for t in tickers:
        if t in have and raw[t]["Close"].notna().sum() > 260:
            close[t] = raw[t]["Close"]
            volume[t] = raw[t]["Volume"]
    close = pd.DataFrame(close).dropna(how="all")
    volume = pd.DataFrame(volume).reindex(close.index)
    return close, volume


def _info(t):
    info = {}
    for attempt in range(3):
        try:
            info = yf.Ticker(t).info or {}
            break
        except Exception:
            time.sleep(2 * (attempt + 1))
    row = {k: info.get(k) for k in FUND_FIELDS}
    row["ticker"] = t
    return row


def get_fundamentals(tickers):
    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(_info, tickers))
    return pd.DataFrame(rows).set_index("ticker")


def _news(t):
    """Headlines from roughly the last 10 days: list of dicts."""
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
        link = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
                or c.get("link"))
        pub = (c.get("provider") or {}).get("displayName") or c.get("publisher")
        if title and (now - ts).days <= 10:
            out.append({"title": title, "link": link, "publisher": pub, "date": ts.strftime("%Y-%m-%d")})
    return t, out


def get_news(tickers):
    with ThreadPoolExecutor(6) as ex:
        return dict(ex.map(_news, tickers))
