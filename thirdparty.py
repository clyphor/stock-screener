"""Two free data services, both optional (each needs a free key as a GitHub secret):

Finnhub (FINNHUB_API_KEY, 60 requests/minute free)
  • analyst recommendation trends (strong buy / buy / hold / sell / strong sell counts per month)
  • company news — used as a backup when Google News fails (North American companies on the free plan)

Financial Modeling Prep (FMP_API_KEY, 250 requests/day free)
  • discounted-cash-flow (DCF) fair value — a third view in the screener's valuation estimate
  • rating snapshot (A–F letter) where the free plan allows it

Everything is cached for a week so the free limits are never a problem; a run only fetches what's missing or old.
"""
import json
import os
import urllib.error
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import diag

CACHE = "results/thirdparty.json"
_lock = threading.Lock()
_last = {"finnhub": 0.0, "fmp": 0.0}
_dead = set()


def _load():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {"finnhub_recs": {}, "fmp": {}}


def _save(c):
    os.makedirs("results", exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(c, f, separators=(",", ":"))


def _get(service, url, gap):
    """GET JSON with spacing between calls; returns None on any failure (and stops after auth/limit errors)."""
    if service in _dead:
        return None
    with _lock:
        wait = _last[service] + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[service] = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "stock-screener/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read()[:200].decode(errors="replace")
        except Exception:
            pass
        b = body.lower()
        if any(w in b for w in ("premium", "subscription", "upgrade", "not available", "access")) and e.code in (401, 402, 403):
            return {"_premium": True}          # this item isn't on the free plan — skip it, keep going
        if e.code in (401, 402, 403):
            _dead.add(service)
            print(f"WARNING {service}: stopped for this run ({e.code} {body[:120]})")
        elif e.code == 429:
            if service == "fmp":
                _dead.add(service)   # daily limit
            else:
                time.sleep(30)
        diag.sample("thirdparty", "errors", f"{service} {e.code} {body[:120]}", market="general")
        return None
    except Exception as e:
        diag.sample("thirdparty", "errors", f"{service} {str(e)[:120]}", market="general")
        return None


def _fresh(entry, days):
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(entry["fetched"]) < timedelta(days=days)
    except Exception:
        return False


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="minutes")


def _symbol(t):
    """Yahoo ticker -> these services' symbol. They mostly cover US listings; others are tried as-is."""
    return t.replace("-", ".") if not t.endswith((".AX", ".KA")) else t


# ---------------------------------------------------------------- Finnhub
def finnhub_recs(tickers, max_calls=300):
    """{ticker: [{period, strongBuy, buy, hold, sell, strongSell}, ...newest first]} — refreshed weekly."""
    key = os.environ.get("FINNHUB_API_KEY")
    c = _load()
    cache = c.setdefault("finnhub_recs", {})
    if key:
        todo = sorted([t for t in tickers if not _fresh(cache.get(t, {}), 7)],
                      key=lambda t: cache.get(t, {}).get("fetched", ""))[:max_calls]
        got = 0
        for t in todo:
            r = _get("finnhub", f"https://finnhub.io/api/v1/stock/recommendation?symbol={urllib.parse.quote(_symbol(t))}&token={key}", 1.1)
            if r is None and "finnhub" in _dead:
                break
            if isinstance(r, list):
                cache[t] = {"fetched": _now(), "trend": r[:4]}
                got += 1
            elif isinstance(r, dict) and r.get("_premium"):
                cache[t] = {"fetched": _now(), "trend": []}
        _save(c)
        diag.put("thirdparty", finnhub_recs_fetched=got, market="general")
    return {t: cache[t]["trend"] for t in tickers if cache.get(t, {}).get("trend")}


def finnhub_news(t, days=10):
    """Company news for one stock, in the same shape as data.py's headlines. [] if unavailable."""
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        return []
    to = datetime.now(timezone.utc).date()
    r = _get("finnhub", f"https://finnhub.io/api/v1/company-news?symbol={urllib.parse.quote(_symbol(t))}"
                        f"&from={to - timedelta(days=days)}&to={to}&token={key}", 1.1)
    out, seen = [], set()
    for n in (r if isinstance(r, list) else [])[:40]:
        title = (n.get("headline") or "").strip()
        if not title or title.lower()[:60] in seen:
            continue
        seen.add(title.lower()[:60])
        out.append({"title": title, "link": n.get("url"), "publisher": n.get("source"),
                    "date": datetime.fromtimestamp(n.get("datetime", 0), timezone.utc).strftime("%Y-%m-%d"),
                    "quality": "quality"})
    return out[:15]


# ---------------------------------------------------------------- Financial Modeling Prep
def fmp_values(tickers, max_calls=120):
    """{ticker: {"dcf": value, "rating": "B+", "score": 1-5}} — refreshed weekly, at most max_calls requests a run
    (the free plan allows 250 a day)."""
    key = os.environ.get("FMP_API_KEY")
    c = _load()
    cache = c.setdefault("fmp", {})
    if key:
        todo = [t for t in tickers if not _fresh(cache.get(t, {}), 7)]
        calls = 0
        for t in todo:
            if calls >= max_calls or "fmp" in _dead:
                break
            s = urllib.parse.quote(_symbol(t))
            e = {"fetched": _now()}
            r = _get("fmp", f"https://financialmodelingprep.com/stable/discounted-cash-flow?symbol={s}&apikey={key}", 0.3)
            calls += 1
            if isinstance(r, list) and r and r[0].get("dcf"):
                e["dcf"] = float(r[0]["dcf"])
                e["dcf_date"] = r[0].get("date")
            r = _get("fmp", f"https://financialmodelingprep.com/stable/ratings-snapshot?symbol={s}&apikey={key}", 0.3)
            calls += 1
            if isinstance(r, list) and r:
                e["rating"], e["score"] = r[0].get("rating"), r[0].get("overallScore")
            cache[t] = e
        _save(c)
        diag.put("thirdparty", fmp_calls=calls, market="general")
    return {t: cache[t] for t in tickers if cache.get(t, {}).get("dcf") or cache.get(t, {}).get("rating")}
