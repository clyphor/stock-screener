"""Why analysts rate a stock the way they do.

Their research reports are paid and private, so this pieces the "why" together from free sources:
  1. recent rating changes (firm, old -> new rating, price target) from Yahoo Finance
  2. analyst headlines among the stock's recent news ("... raises target citing ...")
  3. a short AI summary of those headlines: the main reasons for and the main worries

Everything is cached (results/analyst_why.json) so a run only fetches/asks what's new, staying inside the
free limits. Only stocks that analysts actually cover (3+ analysts) are looked at.
"""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import diag

CACHE = "results/analyst_why.json"
REFRESH_DAYS = 3          # rating changes are re-checked every few days
MAX_FETCH = 120           # Yahoo requests per market per run (spread over runs; oldest first)
MAX_AI = 90               # stocks summarised per market per run (only those with new analyst headlines)
BATCH = 15                # stocks per AI request

ANALYST_RX = re.compile(
    r"\b(upgrad\w*|downgrad\w*|price target|target price|(raises?|lifts?|boosts?|cuts?|lowers?|trims?|slashes?)\b[^.]{0,30}\btarget|"
    r"initiat\w* (coverage|at)|reiterat\w*|overweight|underweight|outperform|underperform|market perform|equal[- ]weight|"
    r"(buy|sell|hold|neutral) rating|rating (on|to)|analysts? (say|see|expect|bullish|bearish)|"
    r"strong buy|top pick|sell-side)\b", re.I)


def _load():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {"actions": {}, "why": {}}


def _save(c):
    os.makedirs("results", exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(c, f, separators=(",", ":"), default=str)


def _now():
    return datetime.now(timezone.utc)


def _fresh(e, days):
    try:
        return _now() - datetime.fromisoformat(e["fetched"]) < timedelta(days=days)
    except Exception:
        return False


def _num(v):
    try:
        v = float(v)
        return round(v, 2) if v == v and v > 0 else None
    except Exception:
        return None


def _fetch_actions(t):
    import yfinance as yf
    df = yf.Ticker(t).upgrades_downgrades
    out = []
    if df is None or len(df) == 0:
        return out
    df = df.sort_index(ascending=False)
    cut = _now() - timedelta(days=180)
    for d, r in df.head(40).iterrows():
        try:
            dt = d.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt < cut:
            break
        out.append({"date": dt.strftime("%Y-%m-%d"), "firm": str(r.get("Firm") or ""), "to": str(r.get("ToGrade") or ""),
                    "from": str(r.get("FromGrade") or ""), "action": str(r.get("Action") or "").lower(),
                    "pt": _num(r.get("currentPriceTarget")), "prior": _num(r.get("priorPriceTarget")),
                    "pt_action": str(r.get("priceTargetAction") or "")})
        if len(out) >= 10:
            break
    return out


def actions(tickers):
    """{ticker: [recent rating changes, newest first]} — cached, refreshed every few days."""
    c = _load()
    cache = c.setdefault("actions", {})
    todo = sorted([t for t in tickers if not _fresh(cache.get(t, {}), REFRESH_DAYS)],
                  key=lambda t: cache.get(t, {}).get("fetched", ""))[:MAX_FETCH]
    got = fails = 0
    for t in todo:
        try:
            cache[t] = {"fetched": _now().isoformat(timespec="minutes"), "list": _fetch_actions(t)}
            got += 1
            fails = 0
        except Exception as e:
            fails += 1
            diag.sample("analyst_why", "errors", f"{t}: {str(e)[:100]}")
            if fails >= 8:   # Yahoo is refusing — try again next run
                break
        time.sleep(0.4)
    _save(c)
    diag.put("analyst_why", actions_fetched=got)
    return {t: cache[t]["list"] for t in tickers if cache.get(t, {}).get("list")}


def headlines(news):
    """The analyst-related headlines among one stock's news items."""
    return [h for h in (news or []) if ANALYST_RX.search(h.get("title") or "")][:8]


def _key(items):
    return hashlib.sha1("|".join(sorted(h.get("title", "")[:80] for h in items)).encode()).hexdigest()[:12]


def summaries(items):
    """items: {ticker: {"name", "rating", "headlines": [...], "changes": [...]}} -> {ticker: {"bull", "bear", "by"}}.
    Asks the AI only for stocks whose analyst headlines changed since the last summary."""
    import claude_api
    c = _load()
    cache = c.setdefault("why", {})
    out, todo = {}, []
    for t, it in items.items():
        k = _key(it["headlines"])
        if cache.get(t, {}).get("key") == k:
            out[t] = cache[t]["why"]
        elif len(it["headlines"]) >= 1:
            todo.append(t)
    todo = todo[:MAX_AI]
    if todo and claude_api.available():
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            blocks = []
            for t in chunk:
                it = items[t]
                ch = "; ".join(f"{a['date']} {a['firm']}: {a['from'] or '-'} -> {a['to']}" + (f", target {a['prior'] or '?'} -> {a['pt']}" if a.get("pt") else "")
                               for a in it.get("changes", [])[:5])
                hl = "\n".join(f"  - {h.get('date', '')} {h.get('title', '')} ({h.get('publisher') or ''})" for h in it["headlines"])
                blocks.append(f"[{t}] {it['name']} — consensus: {it.get('rating') or 'n/a'}\n  rating changes: {ch or 'none listed'}\n{hl}")
            prompt = (
                "You summarise why stock market analysts rate companies the way they do, using ONLY the headlines and "
                "rating changes given. For each stock give up to 3 short reasons analysts are positive (\"bull\") and up "
                "to 2 main worries (\"bear\"), each under 15 words, plain English, no hype. Don't invent facts, numbers or "
                "firms that aren't in the text; if the text gives no reason, return an empty list.\n"
                'Reply with JSON only: {"TICKER": {"bull": ["..."], "bear": ["..."]}, ...}\n\n' + "\n\n".join(blocks))
            try:
                res = claude_api.ask_json(prompt, 3000, "analyst reasons", "object")
            except Exception:
                break   # no AI available right now — the headlines still show; try again next run
            by = claude_api.LAST
            for t in chunk:
                r = res.get(t) or res.get(t.upper()) or {}
                why = {"bull": [str(x)[:140] for x in (r.get("bull") or [])][:3],
                       "bear": [str(x)[:140] for x in (r.get("bear") or [])][:2],
                       "by": by,
                       "date": _now().strftime("%Y-%m-%d")}
                cache[t] = {"key": _key(items[t]["headlines"]), "why": why}
                out[t] = why
    _save(c)
    diag.put("analyst_why", summarised=len(out))
    return out


def build(df, fund, headlines_map):
    """Adds df["an_why"] = {"changes", "headlines", "bull", "bear", "by"} for stocks analysts cover."""
    n = df["analyst_n"] if "analyst_n" in df else None
    covered = [t for t in df.index if n is not None and n.get(t) == n.get(t) and (n.get(t) or 0) >= 3]
    covered.sort(key=lambda t: -float(df.at[t, "score"]))
    try:
        ch = actions(covered)
    except Exception as e:
        print("WARNING analyst rating changes unavailable:", e)
        ch = {}
    items = {}
    for t in covered:
        hl = headlines(headlines_map.get(t, []))
        rating = fund.at[t, "recommendationKey"] if "recommendationKey" in fund and t in fund.index else None
        items[t] = {"name": df.at[t, "name"] if "name" in df else t, "rating": rating if isinstance(rating, str) else None,
                    "headlines": hl, "changes": ch.get(t, [])}
    try:
        why = summaries({t: v for t, v in items.items() if v["headlines"]})
    except Exception as e:
        print("WARNING analyst summaries unavailable:", e)
        why = {}
    res = {}
    for t, it in items.items():
        if not (it["changes"] or it["headlines"]):
            continue
        w = why.get(t, {})
        res[t] = {"changes": it["changes"][:8],
                  "headlines": [{k: h.get(k) for k in ("title", "link", "publisher", "date")} for h in it["headlines"][:6]],
                  "bull": w.get("bull", []), "bear": w.get("bear", []), "by": w.get("by"), "as_of": w.get("date")}
    df["an_why"] = __import__("pandas").Series(res, dtype=object).reindex(df.index)
    diag.put("analyst_why", stocks=len(res), with_changes=sum(1 for v in res.values() if v["changes"]),
             with_reasons=sum(1 for v in res.values() if v["bull"] or v["bear"]))
