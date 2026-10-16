"""Run diagnostics: counters, samples and health checks for every stage, per market.

Every stage calls diag.inc / diag.put / diag.sample. At the end, checks() turns those numbers into
OK / WARN / FAIL lines with a hint saying where to look. Saved in results/runlog.json and shown on the page.
"""
import collections
import threading

_lock = threading.Lock()
MARKET = "general"          # set by run.py before each market runs (markets run one after another)
D = collections.defaultdict(lambda: collections.defaultdict(dict))


def _bucket(stage, market=None):
    return D[market or MARKET][stage]


def put(stage, market=None, **kv):
    with _lock:
        _bucket(stage, market).update(kv)


def inc(stage, key, n=1, market=None):
    with _lock:
        b = _bucket(stage, market)
        b[key] = b.get(key, 0) + n


def sample(stage, key, value, maxn=8, market=None):
    with _lock:
        b = _bucket(stage, market)
        lst = b.setdefault(key, [])
        if len(lst) < maxn and value not in lst:
            lst.append(str(value)[:200])


def snapshot():
    with _lock:
        return {m: {s: dict(v) for s, v in st.items()} for m, st in D.items()}


def _pct(a, b):
    return (a / b) if b else 0.0


def checks(market, stats):
    """Turn the counters for one market into a list of {stage, status, msg, hint}."""
    d = D.get(market, {})
    out = []

    def add(stage, status, msg, hint=""):
        out.append({"stage": stage, "status": status, "msg": msg, "hint": hint})

    u = d.get("universe", {})
    if u:
        src = u.get("source", "?")
        add("Stock list", "OK" if src == "live" else "WARN",
            f"{u.get('count', 0)} tickers from {src}",
            "" if src == "live" else "Index list download failed (Wikipedia / PSX site) — see universe.py; using the saved list.")

    p = d.get("prices", {})
    if p:
        req, got = p.get("requested", 0), p.get("received", 0)
        miss = req - got
        st = "OK" if _pct(miss, req) <= 0.1 else "WARN" if _pct(miss, req) <= 0.5 else "FAIL"
        add("Prices", st, f"{got}/{req} stocks downloaded, {p.get('batch_errors', 0)} batch errors, {p.get('retries', 0)} retries"
            + (f"; last date {p.get('last_date')}" if p.get("last_date") else ""),
            "" if st == "OK" else "Yahoo Finance may be rate-limiting or tickers changed — data.py get_prices; re-run later.")
        if p.get("stale"):
            add("Prices", "WARN", f"{len(p['stale'])} stocks have no price for 5+ days (e.g. {', '.join(p['stale'][:5])})",
                "Possibly suspended or delisted — check the ticker on Yahoo Finance.")

    ix = d.get("index", {})
    if ix:
        add("Index", "OK" if ix.get("used") == ix.get("preferred") else "WARN", f"used {ix.get('used')}",
            "" if ix.get("used") == ix.get("preferred") else "Main index failed to download, a backup was used — data.py get_index.")

    f = d.get("fundamentals", {})
    if f:
        worst = max(((k, v) for k, v in f.items() if k.startswith("missing_")), key=lambda kv: kv[1], default=None)
        st = "OK" if not worst or worst[1] <= 0.4 else "WARN"
        add("Fundamentals", st, f"{f.get('count', 0)} companies; " + ", ".join(
            f"{k[8:]} missing {round(v * 100)}%" for k, v in sorted(f.items()) if k.startswith("missing_") and v > 0.1) or "complete",
            "" if st == "OK" else "Yahoo / PSX pages returned gaps — data.py get_fundamentals / _psx_info.")

    n = d.get("news", {})
    if n:
        reqs, fails = n.get("google_requests", 0), n.get("google_failures", 0)
        cov = stats.get("news_coverage", 0) or 0
        st = "OK" if cov >= 0.7 and _pct(fails, reqs) <= 0.1 else "WARN" if cov >= 0.3 else "FAIL"
        add("Company news", st,
            f"coverage {round(cov * 100)}%; Yahoo items {n.get('yahoo_items', 0)}, Google items {n.get('google_items', 0)}, "
            f"Google requests {reqs} ({fails} failed); dropped: {n.get('dropped_irrelevant', 0)} off-topic, "
            f"{n.get('dropped_lowq', 0)} junk sites, {n.get('dropped_lawfirm_ads', 0)} law-firm ads, {n.get('dropped_promo_cap', 0)} over promo cap",
            "" if st == "OK" else "Google News may be blocking requests — data.py _google_news; errors listed below.")

    h = d.get("health", {})
    if h:
        err = h.get("errors", 0)
        st = "OK" if _pct(err, max(1, h.get("refreshed", 0))) <= 0.2 else "WARN"
        add("Financial health", st, f"{h.get('refreshed', 0)} refreshed, {h.get('cached', 0)} from cache, {err} errors, "
            f"{h.get('with_fscore', 0)} with an F-score",
            "" if st == "OK" else "Yahoo statements unavailable for some companies — data.py _health_one.")

    m = d.get("model", {})
    if m:
        ic = stats.get("ic_mean")
        add("Price model", "OK" if (ic or 0) > 0.02 else "INFO", f"{m.get('train_rows', 0)} training rows; backtest IC {ic}",
            "" if (ic or 0) > 0.02 else "Model isn't predictive in this market right now, so it's down-weighted automatically.")

    c = d.get("claude", {})
    if c:
        calls, fails = c.get("calls", 0), c.get("failures", 0)
        st = "OK" if calls and not fails else "WARN" if calls > fails else "FAIL"
        add("AI (Claude)", st, f"{calls} calls, {fails} failed, {c.get('input_tokens', 0):,} in / {c.get('output_tokens', 0):,} out tokens, "
            f"≈ US${c.get('cost_usd', 0):.3f}",
            "" if st == "OK" else "Check API credit and key in console.anthropic.com; errors listed below.")
    elif stats.get("ai_scoring") == "off":
        add("AI (Claude)", "OK", "off — no API key", "")

    mc = d.get("macro", {})
    if mc.get("requests"):
        reqs, fails = mc.get("requests", 0), mc.get("failures", 0)
        st = "OK" if _pct(fails, reqs) <= 0.2 else "WARN"
        add("Sector & politics", st, f"{mc.get('headlines', 0)} headlines from {reqs} searches ({fails} failed); "
            f"{mc.get('ai_events', 0)} AI events", "" if st == "OK" else "Google News searches failing — macro.py _fetch_all.")
    return out


def errors(market):
    """All sampled error messages for a market, by stage."""
    d = D.get(market, {})
    return {f"{s}.{k}": v for s, st in d.items() for k, v in st.items() if k.startswith("err") and v}


PRICE_IN, PRICE_OUT = 0.10, 0.50   # Claude Haiku 5.5, US$ per million tokens


def claude_ok(resp, market=None):
    u = resp.get("usage", {}) or {}
    i, o = u.get("input_tokens", 0), u.get("output_tokens", 0)
    inc("claude", "calls", market=market)
    inc("claude", "input_tokens", i, market=market)
    inc("claude", "output_tokens", o, market=market)
    with _lock:
        b = _bucket("claude", market)
        b["cost_usd"] = round(b.get("cost_usd", 0) + i / 1e6 * PRICE_IN + o / 1e6 * PRICE_OUT, 5)


def claude_fail(err, where, market=None):
    body = ""
    try:
        body = err.read()[:300].decode(errors="replace")
    except Exception:
        pass
    inc("claude", "calls", market=market)
    inc("claude", "failures", market=market)
    sample("claude", "errors", f"{where}: {err} {body}", market=market)
