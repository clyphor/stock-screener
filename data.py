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


def _download(tickers, period):
    raw = yf.download(tickers, period=period, auto_adjust=True, group_by="ticker",
                      threads=True, progress=False)
    out = {}
    if isinstance(raw.columns, pd.MultiIndex):
        for t in set(raw.columns.get_level_values(0)):
            c = raw[t]["Close"]
            if c.notna().sum() > 260:
                out[t] = (c, raw[t]["Volume"])
    return out


def get_prices(tickers, period, batch=100, tries=3):
    """Return (close, volume) DataFrames. Downloads in batches and retries missing tickers."""
    got, todo = {}, list(dict.fromkeys(tickers))
    for attempt in range(tries):
        if not todo:
            break
        for i in range(0, len(todo), batch):
            try:
                got.update(_download(todo[i:i + batch], period))
            except Exception as e:
                print("download batch failed:", e)
        todo = [t for t in todo if t not in got]
        if todo:
            print(f"retrying {len(todo)} tickers…")
            time.sleep(5 * (attempt + 1))
    if todo:
        print("no price data for:", ", ".join(todo[:30]))
    close = pd.DataFrame({t: v[0] for t, v in got.items()}).dropna(how="all")
    volume = pd.DataFrame({t: v[1] for t, v in got.items()}).reindex(close.index)
    return close[[t for t in tickers if t in close]], volume[[t for t in tickers if t in volume]]


def get_index(candidates, period):
    """First index (or index ETF) that downloads, as a close Series."""
    for t in candidates:
        for attempt in range(3):
            try:
                c = yf.download(t, period=period, auto_adjust=True, progress=False)["Close"]
                c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
                if c.notna().sum() > 260:
                    return c.rename(t)
            except Exception as e:
                print(f"index {t} failed:", e)
            time.sleep(3)
    raise RuntimeError(f"could not download any index from {candidates}")


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
