"""Sector news + political/macro themes -> a 'macro' score for every stock.

How it works
1. Pull ~10 days of Google News headlines for each sector (oil, iron ore, banks…) and for
   each political/macro theme (war, tariffs, elections, interest rates, recession, China).
2. Sector score  = sentiment of that sector's headlines (-1..1).
   Theme heat    = how much that theme is in the news right now (0..1).
3. Each theme has an exposure map: which sectors / industries it helps (+) or hurts (-).
   A stock's macro score = 0.5 * its sector score + sum(theme heat * exposure), clipped to -1..1.

If ANTHROPIC_API_KEY is set, Claude reads the headlines and sets sector scores and theme heat
(much better at nuance). Otherwise a finance word list + headline counts are used.
"""
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import CLAUDE_MODEL
from data import _google_news
from sentiment import lexicon_score

# Sector names match Yahoo Finance's sector field
SECTOR_QUERIES = {
    "Energy": '("oil prices" OR crude OR OPEC OR "gas prices" OR LNG)',
    "Basic Materials": '("iron ore" OR copper OR lithium OR "gold price" OR "mining stocks")',
    "Financial Services": '("bank stocks" OR "bank shares" OR insurers OR "banking sector")',
    "Technology": '("tech stocks" OR semiconductor OR "AI chips" OR "software stocks")',
    "Healthcare": '("healthcare stocks" OR FDA OR "drug prices" OR biotech)',
    "Industrials": '("manufacturing" OR PMI OR "industrial stocks" OR "infrastructure spending")',
    "Consumer Cyclical": '("consumer spending" OR "retail sales" OR "consumer confidence")',
    "Consumer Defensive": '("consumer staples" OR supermarkets OR "food prices")',
    "Utilities": '("utility stocks" OR "electricity prices" OR "power prices")',
    "Real Estate": '(REIT OR "property market" OR "house prices" OR "commercial property")',
    "Communication Services": '("media stocks" OR telecom OR "advertising market")',
}
MARKET_WORD = {"US": "(stocks OR Wall Street)", "ASX": "(ASX OR Australia)"}

# Political / macro themes. Exposures: keys are sectors, or "ind:<industry keyword>", or "*" (all).
THEMES = {
    "war": {
        "label": "War / geopolitical conflict",
        "query": '(war OR invasion OR "missile strike" OR "military conflict" OR "Middle East tensions") markets',
        "exp": {"*": -0.15, "Energy": 0.5, "ind:Aerospace": 0.7, "ind:Gold": 0.6,
                "ind:Airlines": -0.7, "ind:Travel": -0.5, "Consumer Cyclical": -0.25},
    },
    "tariffs": {
        "label": "Tariffs / trade war",
        "query": '(tariff OR tariffs OR "trade war" OR "export ban" OR "trade restrictions")',
        "exp": {"*": -0.1, "Basic Materials": -0.4, "Industrials": -0.35, "Technology": -0.3,
                "Consumer Cyclical": -0.35, "ind:Auto": -0.5, "ind:Semiconductor": -0.4,
                "Utilities": 0.1, "Consumer Defensive": 0.05},
    },
    "rates_down": {
        "label": "Interest-rate cuts",
        "query": '("rate cut" OR "cuts rates" OR "rate cuts" OR "easing") (Fed OR RBA OR "central bank")',
        "exp": {"Real Estate": 0.5, "Utilities": 0.35, "Technology": 0.3, "Consumer Cyclical": 0.3,
                "Financial Services": -0.15, "ind:Banks": -0.25},
    },
    "rates_up": {
        "label": "Interest-rate hikes / sticky inflation",
        "query": '("rate hike" OR "raises rates" OR "higher for longer" OR "inflation surge") (Fed OR RBA OR "central bank")',
        "exp": {"Real Estate": -0.5, "Utilities": -0.35, "Technology": -0.3, "Consumer Cyclical": -0.3,
                "ind:Banks": 0.2, "ind:Insurance": 0.15},
    },
    "election": {
        "label": "Elections / political uncertainty",
        "query": '(election OR midterms OR "government shutdown" OR "political uncertainty") markets',
        "exp": {"*": -0.1, "Healthcare": -0.15, "ind:Defense": 0.1},
    },
    "recession": {
        "label": "Recession / slowdown fears",
        "query": '(recession OR "economic slowdown" OR "job cuts" OR "weak jobs") markets',
        "exp": {"Consumer Cyclical": -0.45, "Industrials": -0.35, "Basic Materials": -0.35,
                "Energy": -0.3, "Financial Services": -0.25, "Consumer Defensive": 0.25,
                "Utilities": 0.25, "Healthcare": 0.2},
    },
    "china": {
        "label": "China stimulus / demand",
        "query": '(China stimulus OR "China demand" OR "China economy") (commodities OR "iron ore" OR markets)',
        "exp": {"Basic Materials": 0.5, "Energy": 0.2, "Industrials": 0.1},
        "markets": ["ASX", "US"],
    },
}


import re
_UP = r"(rise|rises|rising|jump|jumps|surge|surges|soar|soars|climb|climbs|rally|rallies|gain|gains|spike|spikes|higher|record high)"
_DN = r"(fall|falls|falling|drop|drops|slump|slumps|tumble|tumbles|slide|slides|sink|sinks|plunge|plunges|lower|retreat|retreats)"
_COMMOD = r"(oil|crude|brent|wti|gas|lng|iron ore|copper|gold|lithium|coal|nickel|uranium)"


def headline_score(title, sector):
    """Word-list sentiment, but for commodity sectors 'oil prices rise' = good for Energy, etc."""
    t = title.lower()
    if sector in ("Energy", "Basic Materials") and re.search(_COMMOD, t):
        if re.search(_COMMOD + r"[\w\s]{0,20}?" + _UP, t):
            return 0.6
        if re.search(_COMMOD + r"[\w\s]{0,20}?" + _DN, t):
            return -0.6
    return lexicon_score(title)


def _fetch_all(market):
    """Return {('sector', name) | ('theme', key): [headline dicts]} for the last 10 days."""
    jobs = {("sector", s): f"{q} {MARKET_WORD[market]} when:10d" for s, q in SECTOR_QUERIES.items()}
    jobs.update({("theme", k): f"{v['query']} when:10d" for k, v in THEMES.items()})
    with ThreadPoolExecutor(4) as ex:
        res = dict(zip(jobs, ex.map(_google_news, jobs.values())))
    now = datetime.now(timezone.utc)
    out = {}
    for key, items in res.items():
        seen, keep = set(), []
        for i in sorted(items, key=lambda x: x["ts"], reverse=True):
            k = i["title"].lower()[:60]
            if (now - i["ts"]).days <= 10 and k not in seen:
                seen.add(k)
                keep.append({"title": i["title"], "link": i["link"], "publisher": i["publisher"],
                             "date": i["ts"].strftime("%Y-%m-%d")})
        out[key] = keep
    return out


HIST = "results/macro_history.csv"


def _heat(market, counts):
    """Heat 0..1 = how unusual today's headline count is vs that theme's own recent history."""
    os.makedirs("results", exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame(columns=["date", "market", "theme", "n"])
    past = hist[(hist["market"] == market) & (hist["date"] != today)]
    heat = {}
    for k, n in counts.items():
        h = past.loc[past["theme"] == k, "n"].tail(60)
        if len(h) >= 5:
            med = float(h.median())
            z = (n - med) / max(5.0, 0.5 * med)
            heat[k] = float(np.clip(0.35 + 0.35 * z, 0, 1))
        else:  # no baseline yet: scale by volume but cap, so one theme can't dominate
            heat[k] = float(np.clip(n / 100 * 0.6, 0, 0.6))
    rows = pd.DataFrame([{"date": today, "market": market, "theme": k, "n": n} for k, n in counts.items()])
    hist = pd.concat([hist[~((hist["market"] == market) & (hist["date"] == today))], rows], ignore_index=True)
    hist.to_csv(HIST, index=False)
    return heat


def _claude(market, heads):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    blocks = []
    for (kind, name), hs in heads.items():
        label = THEMES[name]["label"] if kind == "theme" else name
        blocks.append(f"## {kind.upper()}: {label}\n" + "\n".join("- " + h["title"] for h in hs[:15]))
    prompt = (f"You are a markets analyst for the {market} stock market. Below are recent headlines grouped "
              "by sector and by political/macro theme.\n\nFor each SECTOR give 'score' from -1 (very bad "
              "news for that sector's stocks) to 1 (very good), and a one-line 'why'.\nFor each THEME give "
              "'heat' from 0 (not a live issue) to 1 (dominating markets right now), and a one-line 'why'.\n"
              "Reply with only JSON: {\"sectors\": {name: {score, why}}, \"themes\": {label: {heat, why}}}.\n\n"
              + "\n\n".join(blocks))
    try:
        body = json.dumps({"model": CLAUDE_MODEL, "max_tokens": 3000,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            text = json.loads(r.read())["content"][0]["text"]
        return json.loads(text[text.index("{"): text.rindex("}") + 1])
    except Exception as e:
        print("Claude macro scoring failed, using word list:", e)
        return None


def macro_context(market, demo=False):
    """Sector scores and theme heat for one market (plus headlines to show on the page)."""
    if demo:
        from demo_data import fake_macro
        heads = fake_macro()
    else:
        heads = _fetch_all(market)

    sectors, themes = {}, {}
    for s in SECTOR_QUERIES:
        hs = heads.get(("sector", s), [])
        for h in hs:
            h["score"] = round(headline_score(h["title"], s), 2)
        score = float(np.mean([h["score"] for h in hs])) * 2 if hs else 0.0  # word list is timid; stretch
        sectors[s] = {"score": round(float(np.clip(score, -1, 1)), 2), "n": len(hs), "why": None,
                      "headlines": hs[:6]}
    heads = {k: v[:15] for k, v in heads.items()}  # trim before sending to Claude
    live = {k: t for k, t in THEMES.items() if market in t.get("markets", [market])}
    heat = _heat(market, {k: len(heads.get(("theme", k), [])) for k in live}) if not demo else \
        {k: min(1.0, len(heads.get(("theme", k), [])) / 10) for k in live}
    for k, t in live.items():
        hs = heads.get(("theme", k), [])
        for h in hs:
            h["score"] = round(lexicon_score(h["title"]), 2)
        themes[k] = {"label": t["label"], "heat": round(heat[k], 2), "n": len(hs), "why": None,
                     "headlines": hs[:6], "exp": t["exp"]}

    method = "wordlist"
    c = _claude(market, heads)
    if c:
        method = "claude"
        for s, v in (c.get("sectors") or {}).items():
            if s in sectors:
                sectors[s].update(score=round(float(np.clip(v.get("score", 0), -1, 1)), 2), why=v.get("why"))
        by_label = {t["label"]: k for k, t in themes.items()}
        for lab, v in (c.get("themes") or {}).items():
            k = by_label.get(lab)
            if k:
                themes[k].update(heat=round(float(np.clip(v.get("heat", 0), 0, 1)), 2), why=v.get("why"))
    total = sum(v["n"] for v in sectors.values()) + sum(v["n"] for v in themes.values())
    print(f"[{market}] macro: {total} sector/theme headlines, scored by {method}")
    return {"sectors": sectors, "themes": themes, "method": method, "headline_count": total}


def _matches(key, sector, industry):
    if key == "*":
        return True
    if key.startswith("ind:"):
        return key[4:].lower() in (industry or "").lower()
    return key == sector


def stock_macro(ctx, sector, industry):
    """(score -1..1, list of (theme label, effect)) for one stock."""
    sec = ctx["sectors"].get(sector, {}).get("score", 0.0)
    effects = []
    for k, t in ctx["themes"].items():
        e = 0.0
        for key, w in t["exp"].items():
            if _matches(key, sector, industry):
                e += w
        e *= t["heat"]
        if abs(e) >= 0.02:
            effects.append((t["label"], round(e, 2)))
    score = float(np.clip(0.5 * sec + sum(e for _, e in effects), -1, 1))
    return round(score, 3), sorted(effects, key=lambda x: -abs(x[1]))


def apply(ctx, df, fund):
    """Add macro_raw (-1..1), macro_effects and sector_news columns to df."""
    ind = fund["industry"].reindex(df.index) if "industry" in fund else pd.Series(None, index=df.index)
    res = {t: stock_macro(ctx, df.at[t, "sector"], ind.get(t)) for t in df.index}
    df["macro_raw"] = pd.Series({t: r[0] for t, r in res.items()})
    df["macro_effects"] = pd.Series({t: r[1] for t, r in res.items()})
    df["sector_news"] = df["sector"].map(lambda s: ctx["sectors"].get(s, {}).get("score", 0.0))
    return df
