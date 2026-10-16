"""Score news headlines: company sentiment, macro/political exposure, peer sentiment.

Uses Claude if ANTHROPIC_API_KEY is set, otherwise a built-in finance word list.
"""
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import CLAUDE_MODEL
import claude_api
import diag
from events import EVENTS, IMPACT, LABEL, classify, event_score

POS = {"beat", "beats", "surge", "surges", "soar", "soars", "jump", "jumps", "rally", "record",
       "upgrade", "upgraded", "raises", "raised", "growth", "profit", "strong", "buyback",
       "outperform", "wins", "win", "approval", "approved", "partnership", "expands", "boost",
       "gains", "rises", "rise", "higher", "bullish", "dividend", "deal", "contract", "tops"}
NEG = {"miss", "misses", "plunge", "plunges", "slump", "falls", "fall", "drop", "drops", "cut",
       "cuts", "downgrade", "downgraded", "lawsuit", "probe", "investigation", "recall", "loss",
       "losses", "weak", "warning", "warns", "layoffs", "fine", "fined", "tariff", "tariffs",
       "ban", "sanctions", "lower", "bearish", "decline", "declines", "slashes", "halt", "fraud"}
MACRO = {"tariff", "tariffs", "election", "fed", "rba", "rates", "rate", "inflation", "sanctions",
         "regulation", "regulator", "antitrust", "ban", "war", "stimulus", "government", "congress",
         "senate", "treasury", "china", "trump", "policy", "tax", "subsidy", "export", "budget"}


def _words(s):
    return re.findall(r"[a-z]+", s.lower())


def lexicon_score(title):
    w = _words(title)
    p = sum(x in POS for x in w)
    n = sum(x in NEG for x in w)
    return (p - n) / (p + n + 1)


def is_macro(title):
    return any(x in MACRO for x in _words(title))


def _claude_batch(items, key):
    """items: list of (ticker, title). Returns list of (score, [event keys])."""
    ev = ", ".join(f"{k} ({v[0]})" for k, v in EVENTS.items())
    prompt = ("For each headline about the named company, judge its likely impact on THAT company's share "
              "price over the next few weeks, from -1 (very negative) to 1 (very positive); 0 if irrelevant "
              "or old news. Also tag the event types it describes using these keys (or [] if none): " + ev +
              ".\nReply with only a JSON array, one object per headline in order: {\"s\": number, \"e\": [keys]}.\n\n"
              + "\n".join(f"{j+1}. [{t}] {h}" for j, (t, h) in enumerate(items)))
    arr = claude_api.ask_json(prompt, 4000, "headline scoring", "array")
    if len(arr) != len(items):
        diag.sample("claude", "errors", f"headline scoring: got {len(arr)} answers for {len(items)} headlines")
        raise ValueError("length mismatch")
    return [(float(np.clip(a.get("s", 0), -1, 1)), [e for e in a.get("e", []) if e in EVENTS]) for a in arr]


def claude_scores(items):
    """items: list of (ticker, title). Returns list of (score, events) from Claude, or None."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not items:
        return None
    chunks = [items[i:i + 60] for i in range(0, len(items), 60)]

    def one(c):  # a failed batch falls back to the rules for just those headlines
        try:
            return _claude_batch(c, key), True
        except Exception as e:
            print("WARNING Claude batch failed, using rules for it:", str(e)[:200])
            return [rule_score(h) for _, h in c], False

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, chunks))
    if not any(ok for _, ok in res):
        return None
    diag.put("claude", headline_batches=len(chunks), headline_batches_ok=sum(ok for _, ok in res))
    return [x for r, _ in res for x in r]


def rule_score(title):
    """Event taxonomy first; plain word list only if no event is recognised."""
    keys = classify(title)
    sc = event_score(keys)
    return (lexicon_score(title) * 0.6 if sc is None else sc), keys


def _recency_weight(date_str, today):
    try:
        days = (today - datetime.strptime(date_str, "%Y-%m-%d").date()).days
    except Exception:
        days = 5
    return 1.0 / (1.0 + max(0, days) / 3.0)  # today 1.0, 3 days ago 0.5, 9 days ago 0.25


def news_features(news, sectors):
    """news: {ticker: [ {title, link, date, ...} ]}, sectors: Series ticker->sector."""
    news = {t: [h if isinstance(h, dict) else {"title": h} for h in hs] for t, hs in news.items()}
    flat = [(t, h["title"]) for t, hs in news.items() for h in hs]
    res = claude_scores(flat)
    method = "claude" if res else "event rules"
    if not res:
        res = [rule_score(h) for _, h in flat]

    today = datetime.now(timezone.utc).date()
    rows = {t: {"news_sent": 0.0, "news_count": 0, "macro_share": 0.0, "macro_sent": 0.0, "events": []}
            for t in news}
    heads = {}
    i = 0
    for t, hs in news.items():
        sc_l, w_l, m_l, evs = [], [], [], {}
        for h in hs:
            sc, keys = res[i]
            i += 1
            mac = is_macro(h["title"])
            w = _recency_weight(h.get("date"), today) * (0.5 if h.get("quality") == "promo" else 1.0)
            sc_l.append(sc); w_l.append(w); m_l.append(mac)
            for k in keys:
                evs[k] = max(evs.get(k, 0), w)  # remember the most recent occurrence
            heads.setdefault(t, []).append({**h, "score": round(float(sc), 2), "macro": mac,
                                            "events": [LABEL[k] for k in keys]})
        if sc_l:
            sc_a, w_a, m_a = np.array(sc_l), np.array(w_l), np.array(m_l)
            rows[t] = {"news_sent": float((sc_a * w_a).sum() / w_a.sum()), "news_count": len(sc_l),
                       "macro_share": float(m_a.mean()), "macro_sent": float(sc_a[m_a].mean()) if m_a.any() else 0.0,
                       "events": sorted(evs, key=lambda k: -abs(IMPACT[k]) * evs[k])}
    df = pd.DataFrame.from_dict(rows, orient="index")

    # Competitor sentiment: average of OTHER companies in the same sector
    sec = sectors.reindex(df.index).fillna("Unknown")
    peer = []
    for t in df.index:
        mates = df.index[(sec == sec[t]) & (df.index != t)]
        peer.append(df.loc[mates, "news_sent"].mean() if len(mates) else 0.0)
    df["peer_sent"] = np.nan_to_num(peer)
    df.attrs["method"] = method
    df.attrs["headlines"] = heads
    return df
