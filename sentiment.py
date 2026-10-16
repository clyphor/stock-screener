"""Score news headlines: company sentiment, macro/political exposure, peer sentiment.

Uses Claude if ANTHROPIC_API_KEY is set, otherwise a built-in finance word list.
"""
import json
import os
import re
import urllib.request

import numpy as np
import pandas as pd

from config import CLAUDE_MODEL

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


def claude_scores(titles):
    """Return list of floats in [-1, 1] from Claude, or None on any failure."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not titles:
        return None
    scores = []
    try:
        for i in range(0, len(titles), 80):
            chunk = titles[i:i + 80]
            prompt = ("Score each stock-news headline for its likely impact on that company's "
                      "share price, from -1 (very negative) to 1 (very positive). Reply with only "
                      "a JSON array of numbers, same order.\n\n" +
                      "\n".join(f"{j+1}. {t}" for j, t in enumerate(chunk)))
            body = json.dumps({"model": CLAUDE_MODEL, "max_tokens": 2000,
                               "messages": [{"role": "user", "content": prompt}]}).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                text = json.loads(r.read())["content"][0]["text"]
            arr = json.loads(text[text.index("["): text.rindex("]") + 1])
            if len(arr) != len(chunk):
                return None
            scores += [float(np.clip(x, -1, 1)) for x in arr]
        return scores
    except Exception as e:
        print("Claude scoring failed, using word list:", e)
        return None


def news_features(news, sectors):
    """news: {ticker: [ {title, link, ...} ]}, sectors: Series ticker->sector."""
    news = {t: [h if isinstance(h, dict) else {"title": h} for h in hs] for t, hs in news.items()}
    flat = [(t, h["title"]) for t, hs in news.items() for h in hs]
    titles = [h for _, h in flat]
    scores = claude_scores(titles)
    method = "claude" if scores else "wordlist"
    if not scores:
        scores = [lexicon_score(h) for h in titles]

    rows = {t: {"news_sent": 0.0, "news_count": 0, "macro_share": 0.0, "macro_sent": 0.0}
            for t in news}
    by_t, heads = {}, {}
    i = 0
    for t, hs in news.items():
        for h in hs:
            sc, mac = scores[i], is_macro(h["title"])
            i += 1
            by_t.setdefault(t, []).append((sc, mac))
            heads.setdefault(t, []).append({**h, "score": round(float(sc), 2), "macro": mac})
    for t, lst in by_t.items():
        s = np.array([x for x, _ in lst])
        m = np.array([y for _, y in lst])
        rows[t] = {"news_sent": s.mean(), "news_count": len(s), "macro_share": m.mean(),
                   "macro_sent": s[m].mean() if m.any() else 0.0}
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
