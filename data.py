"""Download prices, fundamentals and news from Yahoo Finance (free)."""
import json
import os
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

import diag

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
    diag.put("prices", requested=len(todo))
    for attempt in range(tries):
        if not todo:
            break
        for i in range(0, len(todo), batch):
            try:
                got.update(_download(todo[i:i + batch], period))
            except Exception as e:
                print("WARNING download batch failed:", e)
                diag.inc("prices", "batch_errors")
                diag.sample("prices", "errors", f"batch {i}: {e}")
        todo = [t for t in todo if t not in got]
        if todo and attempt < tries - 1:
            print(f"retrying {len(todo)} tickers…")
            diag.inc("prices", "retries")
            time.sleep(5 * (attempt + 1))
    if todo:
        print("WARNING no price data for:", ", ".join(todo[:30]))
        diag.put("prices", missing=todo[:40])
    close = pd.DataFrame({t: v[0] for t, v in got.items()}).dropna(how="all")
    volume = pd.DataFrame({t: v[1] for t, v in got.items()}).reindex(close.index)
    if len(close):
        last_valid = close.apply(lambda c: c.last_valid_index())
        stale = [t for t, d in last_valid.items() if d is not None and (close.index[-1] - d).days > 7]
        diag.put("prices", received=close.shape[1], last_date=str(close.index[-1].date()),
                 first_date=str(close.index[0].date()), stale=stale[:30])
    return close[[t for t in tickers if t in close]], volume[[t for t in tickers if t in volume]]


def get_index(candidates, period):
    """First index (or index ETF) that downloads, as a close Series."""
    for t in candidates:
        for attempt in range(3):
            try:
                c = yf.download(t, period=period, auto_adjust=True, progress=False)["Close"]
                c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
                if c.notna().sum() > 260:
                    diag.put("index", used=t, preferred=candidates[0])
                    return c.rename(t)
            except Exception as e:
                print(f"WARNING index {t} failed:", e)
                diag.sample("index", "errors", f"{t}: {e}")
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


def _psx_info(t, name=None):
    """Fundamentals scraped from dps.psx.com.pk/company/<SYMBOL> (Yahoo has little for Pakistan)."""
    sym = t.replace(".KA", "")
    row = {k: None for k in FUND_FIELDS}
    row["ticker"] = t
    row["psx_sector"] = None
    try:
        req = urllib.request.Request(f"https://dps.psx.com.pk/company/{sym}", headers={"User-Agent": "Mozilla/5.0"})
        page = urllib.request.urlopen(req, timeout=30).read().decode(errors="replace")
    except Exception as e:
        print(f"WARNING [PSX] {sym} page failed: {e}")
        diag.sample("fundamentals", "errors", f"PSX page {sym}: {e}")
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
    tests = {}
    if prof: tests["Profitable (positive profit after tax)"] = prof[0] > 0
    if len(prof) >= 2: tests["Profit growing"] = prof[0] > prof[1]
    if len(prof) >= 3: tests["Profit up two years running"] = prof[0] > prof[1] > prof[2]
    if eps: tests["Positive earnings per share"] = eps[0] > 0
    if len(eps) >= 2: tests["EPS growing"] = eps[0] > eps[1]
    if len(prof) >= 2 and len(eps) >= 2 and prof[1] and eps[1] and eps[0]:
        tests["No dilution (EPS keeping pace with profit)"] = (eps[0] / eps[1]) >= 0.98 * (prof[0] / prof[1])
    if len(tests) >= 3:
        row["f_score"] = round(9 * sum(tests.values()) / len(tests), 1)
        row["f_tests"] = json.dumps(tests)
    if len(sales) >= 2 and len(sales) == len(prof) and sales[1]:
        row["revenueGrowth"] = sales[0] / sales[1] - 1
        if sales[0]:
            row["profitMargins"] = prof[0] / sales[0]
    # Sector: the capitalised line under the company name, e.g. "OIL & GAS EXPLORATION COMPANIES"
    from universe import PSX_SECTORS
    kws = [k.upper() for k, _, _ in PSX_SECTORS] + ["SUGAR", "COMPOSITE", "VANASPATI", "LEATHER", "JUTE", "SYNTHETIC", "WOOLLEN"]
    tok = r"[A-Z&/][A-Z&/\.,'-]*(?![a-z])"
    start = 0
    if name:  # the sector line sits directly under the company name — search only after it
        k = txt.find(name)
        if k < 0:
            k = txt.lower().find(name.lower()[:25])
        start = max(0, k + len(name)) if k >= 0 else 0
    window = txt[start:start + 160] if start else txt
    for cand in re.findall(r"((?:" + tok + r"\s){0,9}" + tok + ")", window):
        if len(cand) < 90 and any(k in cand for k in kws) and cand.strip() != sym:
            row["psx_sector"] = cand.strip()
            break
    row["currency"] = "PKR"
    return row


def get_fundamentals(tickers, names=None):
    if tickers and all(t.endswith(".KA") for t in tickers):
        names = names or {}
        with ThreadPoolExecutor(6) as ex:
            return pd.DataFrame(list(ex.map(lambda t: _psx_info(t, names.get(t)), tickers))).set_index("ticker")
    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(_info, tickers))
    return pd.DataFrame(rows).set_index("ticker")


def _yahoo_news(t):
    out = []
    try:
        tk = yf.Ticker(t)
        items = tk.get_news(count=15) if hasattr(tk, "get_news") else tk.news
    except Exception as e:
        items = []
        diag.inc("news", "yahoo_failures")
        diag.sample("news", "errors", f"Yahoo news {t}: {e}")
    diag.inc("news", "yahoo_items", len(items or []))
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


def _google_news(query, market="ASX", stage="news"):
    """Google News RSS search: free, current, covers US, ASX and Pakistan."""
    hl, gl = LOCALE.get(market, ("en-AU", "AU"))
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + f"&hl={hl}&gl={gl}&ceid={gl}:en")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (stock-screener)"})
    out = []
    diag.inc(stage, "google_requests" if stage == "news" else "requests")
    err = None
    for attempt in range(3):
        try:
            root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
            break
        except Exception as e:
            err = e
            time.sleep(2 * (attempt + 1))
    else:
        diag.inc(stage, "google_failures" if stage == "news" else "failures")
        diag.sample(stage, "errors", f"Google News: {err}")
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
    diag.inc(stage, "google_items" if stage == "news" else "headlines", len(out))
    return out


def _clean_name(name):
    """'Alphabet Inc. (Class A)' -> 'Alphabet'; keeps meaningful words like Group/Holdings."""
    name = re.sub(r"\[.*?\]|\(.*?\)", "", str(name or ""))
    name = re.sub(r"[,]?\s+(Inc\.?|Corporation|Corp\.?|Ltd\.?|Limited|plc|N\.V\.|S\.A\.|Co\.|Common Stock.*|Class [A-C].*)$",
                  "", name.strip(), flags=re.I)
    name = re.sub(r"[,]?\s+(Inc\.?|Corporation|Corp\.?|Ltd\.?|Limited|plc)$", "", name.strip(), flags=re.I)
    return re.sub(r"\s+", " ", name).strip(" .,&")


# Auto-generated price-tick sites: lots of headlines, no information
# US "shareholder alert" ads from class-action law firms — not real news about the company
LAW_FIRM_SPAM = re.compile(
    r"(rosen law|pomerantz|levi & korsinsky|bragar eagel|faruqi|bronstein|kessler topaz|glancy|schall law|"
    r"robbins geller|robbins llp|johnson fistel|kahn swick|gainey mckenna|bernstein liebhard|block & leviton|"
    r"hagens berman|portnoy law|frank r\. cruz|holzer|khang & khang|rigrodsky|halper sadeh|ademi|monteverde|"
    r"shareholder alert|investor alert|class action (reminder|filed|lawsuit filed)|lead plaintiff deadline|"
    r"investors who lost money|encourages investors|announces investigation|investigation on behalf)", re.I)
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
    items = []  # Yahoo's news endpoint rate-limits large runs; Google News covers everything we need
    items += _google_news(f'"{nm}" ({sites}) when:10d', market) if sites else []
    items += _google_news(f'"{nm}" {ctx} when:10d', market)
    seen, out, promo = set(), [], 0
    for i in sorted(items, key=lambda x: x["ts"], reverse=True):
        key = i["title"].lower()[:60]
        pub = (i["publisher"] or "").lower()
        if (now - i["ts"]).days > 10 or key in seen:
            continue
        if pub in LOW_QUALITY:
            diag.inc("news", "dropped_lowq")
            continue
        if LAW_FIRM_SPAM.search(i["title"]) or LAW_FIRM_SPAM.search(pub):
            diag.inc("news", "dropped_lawfirm_ads")
            continue
        if not _relevant(i["title"], name, code, strict=(market == "PSX")):
            diag.inc("news", "dropped_irrelevant")
            continue
        q = quality_of(i["publisher"])
        if q == "promo":
            if promo >= 3:
                diag.inc("news", "dropped_promo_cap")
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
    with ThreadPoolExecutor(10) as ex:
        res = dict(ex.map(_news, [(t, names.get(t) or t, market) for t in tickers]))
    n = sum(1 for v in res.values() if v)
    print(f"[{market}] news: {n}/{len(res)} stocks have headlines, {sum(map(len, res.values()))} total")
    diag.put("news", stocks=len(res), with_news=n, kept=sum(map(len, res.values())),
             no_news_sample=[t for t, v in res.items() if not v][:15])
    return res


# ---------------------------------------------------------------- financial health
HEALTH_CACHE = "results/health.csv"
HEALTH_VERSION = 2   # bump when new fields are added, so cached rows refresh


def _row(df, *names):
    """First matching line item from a yfinance statement (columns = years, newest first)."""
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            s = pd.to_numeric(df.loc[n], errors="coerce")
            return s if s.notna().any() else None
    return None


def _v(s, i):
    try:
        x = float(s.iloc[i])
        return x if x == x else None
    except Exception:
        return None


def _health_one(args):
    """Piotroski F-score (9 tests), Altman Z, interest cover, cash conversion, dilution, margin trend."""
    t, mcap, sector = args
    out = {"ticker": t}
    try:
        tk = yf.Ticker(t)
        inc, bal, cf = tk.income_stmt, tk.balance_sheet, tk.cashflow
    except Exception as e:
        out["error"] = str(e)[:100]
        return out
    ni = _row(inc, "Net Income", "Net Income Common Stockholders")
    rev = _row(inc, "Total Revenue", "Operating Revenue")
    gp = _row(inc, "Gross Profit")
    ebit = _row(inc, "EBIT", "Operating Income")
    intexp = _row(inc, "Interest Expense", "Interest Expense Non Operating")
    ta = _row(bal, "Total Assets")
    ca = _row(bal, "Current Assets")
    cl = _row(bal, "Current Liabilities")
    ltd = _row(bal, "Long Term Debt", "Long Term Debt And Capital Lease Obligation")
    tl = _row(bal, "Total Liabilities Net Minority Interest", "Total Liabilities")
    re_ = _row(bal, "Retained Earnings")
    sh = _row(bal, "Ordinary Shares Number", "Share Issued")
    cfo = _row(cf, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    # For the Shariah screen
    debt = _row(bal, "Total Debt")
    cash = _row(bal, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    intinc = _row(inc, "Interest Income", "Interest Income Non Operating")
    out.update(total_debt=_v(debt, 0), cash=_v(cash, 0), interest_income=_v(intinc, 0), revenue=_v(rev, 0))

    tests = {}
    roa0 = _v(ni, 0) / _v(ta, 0) if _v(ni, 0) is not None and _v(ta, 0) else None
    roa1 = _v(ni, 1) / _v(ta, 1) if _v(ni, 1) is not None and _v(ta, 1) else None
    if roa0 is not None: tests["Profitable (positive return on assets)"] = roa0 > 0
    if _v(cfo, 0) is not None: tests["Positive operating cash flow"] = _v(cfo, 0) > 0
    if roa0 is not None and roa1 is not None: tests["Return on assets improving"] = roa0 > roa1
    if _v(cfo, 0) is not None and _v(ni, 0) is not None: tests["Cash flow higher than reported profit"] = _v(cfo, 0) > _v(ni, 0)
    if _v(ltd, 0) is not None and _v(ltd, 1) is not None and _v(ta, 0) and _v(ta, 1):
        tests["Debt falling relative to assets"] = _v(ltd, 0) / _v(ta, 0) <= _v(ltd, 1) / _v(ta, 1)
    if all(_v(x, i) for x in (ca, cl) for i in (0, 1)):
        tests["Short-term liquidity improving"] = _v(ca, 0) / _v(cl, 0) > _v(ca, 1) / _v(cl, 1)
    if _v(sh, 0) and _v(sh, 1): tests["No new shares issued"] = _v(sh, 0) <= _v(sh, 1) * 1.01
    if all(_v(x, i) for x in (gp, rev) for i in (0, 1)):
        tests["Gross margin improving"] = _v(gp, 0) / _v(rev, 0) > _v(gp, 1) / _v(rev, 1)
    if all(_v(x, i) for x in (rev, ta) for i in (0, 1)):
        tests["Asset turnover improving"] = _v(rev, 0) / _v(ta, 0) > _v(rev, 1) / _v(ta, 1)
    if len(tests) >= 5:
        out["f_score"] = round(9 * sum(tests.values()) / len(tests), 1)
        out["f_tests"] = json.dumps({k: bool(v) for k, v in tests.items()})

    # Altman Z (not meaningful for banks/insurers)
    if sector != "Financial Services" and _v(ta, 0) and _v(tl, 0):
        wc = (_v(ca, 0) or 0) - (_v(cl, 0) or 0)
        z = (1.2 * wc + 1.4 * (_v(re_, 0) or 0) + 3.3 * (_v(ebit, 0) or 0) + 1.0 * (_v(rev, 0) or 0)) / _v(ta, 0) \
            + 0.6 * (mcap or 0) / _v(tl, 0)
        out["altman_z"] = round(z, 2)
    if _v(ebit, 0) is not None and _v(intexp, 0):
        out["interest_cover"] = round(_v(ebit, 0) / abs(_v(intexp, 0)), 1)
    if _v(cfo, 0) is not None and _v(ni, 0) and _v(ni, 0) > 0:
        out["cash_conversion"] = round(_v(cfo, 0) / _v(ni, 0), 2)
    if _v(sh, 0) and _v(sh, 1):
        out["dilution"] = round(_v(sh, 0) / _v(sh, 1) - 1, 3)
    if all(_v(x, i) for x in (ebit, rev) for i in (0, 2)):
        out["margin_trend"] = round(_v(ebit, 0) / _v(rev, 0) - _v(ebit, 2) / _v(rev, 2), 3)
    out["asof"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out["v"] = HEALTH_VERSION
    return out


def get_health(tickers, mcaps, sectors, market, max_age_days=7):
    """Statements only change quarterly, so results are cached for a week in results/health.csv."""
    cache = pd.read_csv(HEALTH_CACHE, index_col="ticker") if os.path.exists(HEALTH_CACHE) else pd.DataFrame()
    today = datetime.now(timezone.utc).date()
    fresh = set()
    if len(cache) and "asof" in cache:
        age = (pd.Timestamp(today) - pd.to_datetime(cache["asof"], errors="coerce")).dt.days
        ver = cache["v"] if "v" in cache else pd.Series(0, index=cache.index)
        fresh = set(cache.index[(age <= max_age_days) & (ver.fillna(0) >= HEALTH_VERSION)])
    todo = [t for t in tickers if t not in fresh and not t.endswith(".KA")]
    if todo:
        with ThreadPoolExecutor(6) as ex:
            rows = list(ex.map(_health_one, [(t, mcaps.get(t), sectors.get(t)) for t in todo]))
        new = pd.DataFrame(rows).set_index("ticker")
        errs = new["error"].dropna() if "error" in new else pd.Series(dtype=str)
        diag.put("health", errors=int(len(errs)))
        for t, e in errs.head(8).items():
            diag.sample("health", "errors", f"{t}: {e}")
        cache = pd.concat([cache.drop(index=[t for t in new.index if t in cache.index], errors="ignore"), new])
        os.makedirs("results", exist_ok=True)
        cache.to_csv(HEALTH_CACHE, index_label="ticker")
    print(f"[{market}] financial health: {len(todo)} refreshed, {len([t for t in tickers if t in fresh])} from cache")
    out = cache.reindex(tickers)
    diag.put("health", refreshed=len(todo), cached=len([t for t in tickers if t in fresh]),
             with_fscore=int(out["f_score"].notna().sum()) if "f_score" in out else 0)
    return out
