"""Download prices, fundamentals and news from Yahoo Finance (free)."""
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import yfinance as yf

FUND_FIELDS = [
    "shortName", "longName", "sector", "industry", "currency", "marketCap", "trailingPE",
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


def _yahoo_news(t):
    out = []
    try:
        tk = yf.Ticker(t)
        items = tk.get_news(count=15) if hasattr(tk, "get_news") else tk.news
    except Exception:
        items = []
    for it in items or []:
        c = it.get("content", it)  # yfinance changed format; handle both
        when = c.get("pubDate") or c.get("providerPublishTime")
        try:
            ts = (datetime.fromtimestamp(when, timezone.utc) if isinstance(when, (int, float))
                  else datetime.fromisoformat(str(when).replace("Z", "+00:00")))
        except Exception:
            continue
        link = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
                or c.get("link"))
        pub = (c.get("provider") or {}).get("displayName") or c.get("publisher")
        if c.get("title"):
            out.append({"title": c["title"], "link": link, "publisher": pub, "ts": ts})
    return out


def _google_news(query):
    """Google News RSS search: free, current, covers US and ASX."""
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=en-AU&gl=AU&ceid=AU:en")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (stock-screener)"})
    out = []
    for attempt in range(3):
        try:
            root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
            break
        except Exception:
            time.sleep(2 * (attempt + 1))
    else:
        return out
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        src = item.find("source")
        pub = src.text if src is not None else None
        if pub and title.endswith(" - " + pub):
            title = title[: -len(pub) - 3]
        try:
            ts = parsedate_to_datetime(item.findtext("pubDate"))
        except Exception:
            continue
        out.append({"title": title, "link": item.findtext("link"), "publisher": pub, "ts": ts})
    return out


def _clean_name(name):
    """'Alphabet Inc. (Class A)' -> 'Alphabet'; keeps meaningful words like Group/Holdings."""
    name = re.sub(r"\[.*?\]|\(.*?\)", "", str(name or ""))
    name = re.sub(r"[,]?\s+(Inc\.?|Corporation|Corp\.?|Ltd\.?|Limited|plc|N\.V\.|S\.A\.|Co\.|Common Stock.*|Class [A-C].*)$",
                  "", name.strip(), flags=re.I)
    name = re.sub(r"[,]?\s+(Inc\.?|Corporation|Corp\.?|Ltd\.?|Limited|plc)$", "", name.strip(), flags=re.I)
    return re.sub(r"\s+", " ", name).strip(" .,&")


def _news(args):
    """Headlines from the last 10 days, newest first. Yahoo first, Google News to fill gaps."""
    t, name, market = args
    now = datetime.now(timezone.utc)
    items = _yahoo_news(t)
    if len([i for i in items if (now - i["ts"]).days <= 10]) < 3:
        code = t.replace(".AX", "")
        q = (f'"{_clean_name(name)}" (ASX OR shares OR stock)' if market == "ASX"
             else f'"{_clean_name(name)}" (stock OR shares OR NYSE OR Nasdaq)') + " when:10d"
        items += _google_news(q)
    seen, out = set(), []
    for i in sorted(items, key=lambda x: x["ts"], reverse=True):
        key = i["title"].lower()[:60]
        if (now - i["ts"]).days <= 10 and key not in seen:
            seen.add(key)
            out.append({"title": i["title"], "link": i["link"], "publisher": i["publisher"],
                        "date": i["ts"].strftime("%Y-%m-%d")})
    return t, out[:15]


def get_news(tickers, names, market):
    with ThreadPoolExecutor(4) as ex:
        res = dict(ex.map(_news, [(t, names.get(t) or t, market) for t in tickers]))
    n = sum(1 for v in res.values() if v)
    print(f"[{market}] news: {n}/{len(res)} stocks have headlines, {sum(map(len, res.values()))} total")
    return res
