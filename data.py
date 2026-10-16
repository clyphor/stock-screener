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


def _num_list(txt, label, n=4):
    m = re.search(re.escape(label) + r"((?:\s+\(?-?[\d,]+(?:\.\d+)?\)?){1,%d})" % n, txt)
    if not m:
        return []
    vals = []
    for v in m.group(1).split():
        neg = v.startswith("(")
        v = v.strip("()").replace(",", "")
        try:
            vals.append(-float(v) if neg else float(v))
        except ValueError:
            pass
    return vals


def _psx_info(t):
    """Fundamentals scraped from dps.psx.com.pk/company/<SYMBOL> (Yahoo has little for Pakistan)."""
    sym = t.replace(".KA", "")
    row = {k: None for k in FUND_FIELDS}
    row["ticker"] = t
    row["psx_sector"] = None
    try:
        req = urllib.request.Request(f"https://dps.psx.com.pk/company/{sym}", headers={"User-Agent": "Mozilla/5.0"})
        page = urllib.request.urlopen(req, timeout=30).read().decode(errors="replace")
    except Exception as e:
        print(f"[PSX] {sym} page failed: {e}")
        return row
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)).replace("&nbsp;", " ")
    g = lambda rx: (lambda m: m.group(1) if m else None)(re.search(rx, txt))
    try:
        row["trailingPE"] = float(g(r"P/E Ratio \(TTM\)\s*\**\s*(-?[\d.,]+)").replace(",", ""))
    except Exception:
        pass
    try:
        row["marketCap"] = float(g(r"Market Cap \(000'\s*s\s*\)\s*([\d.,]+)").replace(",", "")) * 1000
    except Exception:
        pass
    ann = txt[txt.find("Annual"):] if "Annual" in txt else txt
    eps, prof, sales = _num_list(ann, "EPS"), _num_list(ann, "Profit after Taxation"), _num_list(ann, "Sales")
    if len(eps) >= 2 and eps[1]:
        row["earningsGrowth"] = eps[0] / abs(eps[1]) - 1
    if len(sales) >= 2 and len(sales) == len(prof) and sales[1]:
        row["revenueGrowth"] = sales[0] / sales[1] - 1
        if sales[0]:
            row["profitMargins"] = prof[0] / sales[0]
    # Sector: the capitalised line under the company name, e.g. "OIL & GAS EXPLORATION COMPANIES"
    from universe import PSX_SECTORS
    kws = [k.upper() for k, _, _ in PSX_SECTORS] + ["SUGAR", "COMPOSITE", "VANASPATI", "LEATHER", "JUTE", "SYNTHETIC", "WOOLLEN"]
    tok = r"[A-Z&/][A-Z&/\.,'-]*(?![a-z])"
    for cand in re.findall(r"((?:" + tok + r"\s){0,9}" + tok + ")", txt):
        if len(cand) < 90 and any(k in cand for k in kws) and cand.strip() != sym:
            row["psx_sector"] = cand.strip()
            break
    row["currency"] = "PKR"
    return row


def get_fundamentals(tickers):
    if tickers and all(t.endswith(".KA") for t in tickers):
        with ThreadPoolExecutor(4) as ex:
            return pd.DataFrame(list(ex.map(_psx_info, tickers))).set_index("ticker")
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


LOCALE = {"US": ("en-US", "US"), "ASX": ("en-AU", "AU"), "PSX": ("en-PK", "PK")}


def _google_news(query, market="ASX"):
    """Google News RSS search: free, current, covers US, ASX and Pakistan."""
    hl, gl = LOCALE.get(market, ("en-AU", "AU"))
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + f"&hl={hl}&gl={gl}&ceid={gl}:en")
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


# Auto-generated price-tick sites: lots of headlines, no information
LOW_QUALITY = {"ad-hoc-news.de", "marketbeat", "marketbeat.com", "defense world", "etf daily news",
               "the lincolnian online", "modern readers", "watchlist news", "zolmax", "ticker report",
               "american banking news", "the cerbat gem", "dailypolitical.com", "stocktitan.net",
               "youtube", "facebook", "instagram", "x.com", "tiktok", "linkedin", "reddit", "pinterest",
               "cricinfo", "espncricinfo", "geo super", "cricbuzz"}
_STOP = {"the", "and", "group", "holdings", "company", "corp", "resources", "energy", "bank", "limited",
         "international", "financial", "technologies", "services", "trust", "of", "&"}


# Reputable outlets searched directly (Google News "site:" filter), per market
QUALITY_SITES = {
    "US": ["reuters.com", "cnbc.com", "wsj.com", "bloomberg.com", "marketwatch.com", "barrons.com",
           "apnews.com", "ft.com", "nytimes.com", "investors.com", "finance.yahoo.com"],
    "ASX": ["afr.com", "theaustralian.com.au", "abc.net.au", "smh.com.au", "reuters.com", "bloomberg.com",
            "theguardian.com", "news.com.au", "marketindex.com.au", "fool.com.au", "stockhead.com.au",
            "livewiremarkets.com", "theaustralian.com.au", "itnews.com.au", "miningweekly.com"],
    "PSX": ["dawn.com", "tribune.com.pk", "brecorder.com", "thenews.com.pk", "profit.pakistantoday.com.pk",
            "mettisglobal.news", "arynews.tv", "geo.tv", "reuters.com", "bloomberg.com", "propakistani.pk"],
}
# Content farms / promotional sites: kept but capped and down-weighted
PROMO = {"kalkine", "kalkine media", "simply wall st", "simply wall street", "tipranks", "stocks down under",
         "ad hoc news", "thebull.com.au", "investing.com", "benzinga", "zacks", "seeking alpha",
         "insidermonkey", "yahoo! finance canada", "the globe and mail", "gurufocus", "www.marketscreener.com"}


def quality_of(pub):
    p = (pub or "").lower()
    return "promo" if p in PROMO or "kalkine" in p else "normal"


_GENERIC = {"oil", "gas", "development", "cement", "power", "pakistan", "national", "united", "first", "general",
            "global", "fertilizer", "fertiliser", "textile", "mills", "motor", "motors", "sugar", "petroleum",
            "engineering", "industries", "chemical", "chemicals", "steel", "insurance", "foods", "investment"}


def _relevant(title, name, code, strict=False):
    """Keep a headline only if it names the company (or its ticker).
    strict (Pakistan): company names are often generic ('Oil & Gas Development'), so require the
    ticker, or two distinctive name words, or the one distinctive word if that's all there is."""
    t = title.lower()
    if re.search(r"\b" + re.escape(code.lower()) + r"\b", t) and len(code) >= 3:
        return True
    words = [w for w in re.findall(r"[a-z0-9]+", _clean_name(name).lower()) if w not in _STOP and len(w) >= 3]
    if not strict:
        return bool(words) and words[0] in t
    distinct = [w for w in words if w not in _GENERIC]
    hits = [w for w in words if re.search(r"\b" + re.escape(w) + r"\b", t)]
    if len(words) >= 2 and len(hits) >= 2:
        return True
    return len(distinct) == 1 and distinct[0] in hits and len(distinct[0]) >= 4


def _news(args):
    """Headlines from the last 10 days, newest first.
    Sources: Yahoo, Google News restricted to reputable outlets, then general Google News.
    Promotional sites are capped at 3 per stock and marked so they count half."""
    t, name, market = args
    now = datetime.now(timezone.utc)
    code = t.replace(".AX", "").replace(".KA", "")
    nm = _clean_name(name)
    sites = " OR ".join(f"site:{d}" for d in QUALITY_SITES.get(market, []))
    ctx = {"ASX": "(ASX OR shares OR stock)", "US": "(stock OR shares OR NYSE OR Nasdaq)",
           "PSX": "(PSX OR shares OR stock OR Pakistan)"}.get(market, "(stock OR shares)")
    items = _yahoo_news(t)
    items += _google_news(f'"{nm}" ({sites}) when:10d', market) if sites else []
    items += _google_news(f'"{nm}" {ctx} when:10d', market)
    seen, out, promo = set(), [], 0
    for i in sorted(items, key=lambda x: x["ts"], reverse=True):
        key = i["title"].lower()[:60]
        pub = (i["publisher"] or "").lower()
        if (now - i["ts"]).days > 10 or key in seen or pub in LOW_QUALITY or not _relevant(i["title"], name, code, strict=(market == "PSX")):
            continue
        q = quality_of(i["publisher"])
        if q == "promo":
            if promo >= 3:
                continue
            promo += 1
        seen.add(key)
        out.append({"title": i["title"], "link": i["link"], "publisher": i["publisher"],
                    "date": i["ts"].strftime("%Y-%m-%d"), "quality": q})
    # Reputable sources first, then newest
    out.sort(key=lambda h: (h["quality"] == "promo", h["date"]), reverse=False)
    out.sort(key=lambda h: h["date"], reverse=True)
    out.sort(key=lambda h: h["quality"] == "promo")
    return t, out[:15]


def get_news(tickers, names, market):
    with ThreadPoolExecutor(4) as ex:
        res = dict(ex.map(_news, [(t, names.get(t) or t, market) for t in tickers]))
    n = sum(1 for v in res.values() if v)
    print(f"[{market}] news: {n}/{len(res)} stocks have headlines, {sum(map(len, res.values()))} total")
    return res
