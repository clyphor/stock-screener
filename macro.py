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
MARKET_WORD = {"US": "(stocks OR Wall Street)", "ASX": "(ASX OR Australia OR Australian)",
               "PSX": "(Pakistan OR PSX OR KSE)"}
# Themes get a local angle for each market, and promotional/micro-cap sites are excluded
THEME_CONTEXT = {"US": "", "ASX": " (Australia OR Australian OR ASX OR RBA OR Canberra)", "PSX": ""}
EXCLUDE = (" -site:kalkinemedia.com -site:simplywall.st -site:tipranks.com -site:stocksdownunder.com"
           " -site:youtube.com -site:facebook.com -site:instagram.com -site:x.com -site:tiktok.com")

# Political / macro / sector themes.
# Exposure keys: a sector name, "ind:<text in Yahoo industry>", "tk:<ticker>", or "*" (every stock).
# Values: how much the theme helps (+) or hurts (-) at full heat. Split by direction where it matters
# (e.g. oil supply up vs down), because the same topic can be good or bad depending on what happened.
T = lambda label, query, exp, markets=None: {"label": label, "query": query, "exp": exp,
                                             **({"markets": markets} if markets else {})}
THEMES = {
    # --- Geopolitics -----------------------------------------------------------------------
    "war": T("War / geopolitical conflict",
        '(war OR invasion OR "missile strike" OR airstrike OR "military conflict" OR escalation) (markets OR stocks OR oil)',
        {"*": -0.15, "Energy": 0.4, "ind:Aerospace": 0.7, "ind:Gold": 0.6, "ind:Airlines": -0.7,
         "ind:Travel": -0.5, "ind:Lodging": -0.3, "Consumer Cyclical": -0.2}),
    "ceasefire": T("Ceasefire / peace deal",
        '(ceasefire OR "peace deal" OR "peace talks" OR truce OR "end of war") (markets OR stocks OR oil)',
        {"*": 0.1, "Energy": -0.3, "ind:Aerospace": -0.3, "ind:Gold": -0.3, "ind:Airlines": 0.4,
         "ind:Travel": 0.3, "ind:Building Materials": 0.15, "ind:Engineering": 0.15}),
    "china_tensions": T("US–China / Taiwan tensions",
        '(Taiwan OR "South China Sea" OR "US-China tensions" OR "China sanctions" OR "decoupling")',
        {"*": -0.05, "ind:Semiconductor": -0.35, "ind:Consumer Electronics": -0.3, "Basic Materials": -0.15,
         "ind:Aerospace": 0.3, "ind:Other Industrial Metals": 0.2}),
    "critical_minerals": T("Critical minerals / rare-earth deals",
        '("critical minerals" OR "rare earths" OR "rare earth" OR lithium OR cobalt OR graphite OR antimony) '
        '(deal OR agreement OR pact OR "supply chain" OR "export ban" OR "export controls" OR stockpile OR offtake)',
        {"ind:Other Industrial Metals": 0.45, "ind:Other Precious Metals": 0.2, "ind:Copper": 0.15,
         "tk:LYC.AX": 0.6, "tk:ILU.AX": 0.45, "tk:MP": 0.6, "tk:ALB": 0.3, "tk:PLS.AX": 0.3,
         "tk:MIN.AX": 0.2, "tk:IGO.AX": 0.25, "tk:SFR.AX": 0.15, "ind:Uranium": 0.1, "ind:Semiconductor": -0.05}),
    "sanctions": T("New sanctions on major producers",
        '(sanctions OR embargo OR "price cap") (Russia OR Iran OR Venezuela OR China) (oil OR gas OR metals OR exports)',
        {"ind:Oil & Gas E&P": 0.35, "ind:Oil & Gas Integrated": 0.25, "ind:Refining": -0.1,
         "ind:Aluminum": 0.2, "ind:Steel": 0.1, "ind:Airlines": -0.2}),
    # --- Oil & energy supply --------------------------------------------------------------
    "oil_supply_down": T("Oil supply disruption / OPEC cuts",
        '("OPEC cut" OR "output cut" OR "production cut" OR "Strait of Hormuz" OR "supply disruption" '
        'OR "pipeline attack" OR "refinery attack" OR "tanker attack") oil',
        {"*": -0.05, "ind:Oil & Gas E&P": 0.6, "ind:Oil & Gas Integrated": 0.45, "ind:Oil & Gas Midstream": 0.2,
         "ind:Oil & Gas Equipment": 0.3, "ind:Airlines": -0.5, "ind:Trucking": -0.2, "ind:Chemicals": -0.15}),
    "oil_supply_up": T("More oil supply (new reserves, OPEC hikes, Venezuela/Iran barrels)",
        '("OPEC increase" OR "raise output" OR "boost output" OR "oil glut" OR oversupply OR "new oil discovery" '
        'OR "oil reserves" OR "Venezuela oil" OR "Venezuelan oil" OR "sanctions lifted" OR "Iran oil exports" OR "record output")',
        {"ind:Oil & Gas E&P": -0.5, "ind:Oil & Gas Integrated": -0.35, "ind:Oil & Gas Equipment": -0.2,
         "ind:Refining": 0.3, "ind:Airlines": 0.35, "ind:Trucking": 0.1, "ind:Chemicals": 0.1}),
    "drilling_policy": T("Pro-drilling / LNG approvals policy",
        '("drilling permits" OR "LNG approvals" OR "LNG export" OR "oil leasing" OR "expand drilling" '
        'OR "gas approvals" OR "offshore drilling") (government OR administration OR policy OR approves)',
        {"ind:Oil & Gas Equipment": 0.4, "ind:Oil & Gas Midstream": 0.3, "ind:Oil & Gas E&P": 0.1, "ind:Solar": -0.2}, ["US", "ASX"]),
    "climate_policy": T("Climate & clean-energy policy",
        '("carbon tax" OR "emissions target" OR "clean energy" OR renewables OR "Inflation Reduction Act" OR "net zero") '
        '(policy OR subsidies OR credits OR law OR government)',
        {"ind:Solar": 0.4, "ind:Utilities - Renewable": 0.4, "ind:Coal": -0.4, "ind:Uranium": 0.15,
         "Energy": -0.1, "ind:Auto Manufacturers": 0.05}),
    # --- Trade ----------------------------------------------------------------------------
    "tariffs": T("New tariffs / trade war",
        '(tariff OR tariffs OR "trade war" OR "export ban" OR "trade restrictions") (new OR threat OR imposes OR raises OR hike)',
        {"*": -0.1, "Basic Materials": -0.35, "Industrials": -0.3, "Technology": -0.25, "Consumer Cyclical": -0.3,
         "ind:Auto": -0.45, "ind:Semiconductor": -0.35, "ind:Farm": -0.3, "ind:Steel": 0.25, "Utilities": 0.1}),
    "trade_deal": T("Trade deals / tariff relief",
        '("trade deal" OR "trade agreement" OR "tariff relief" OR "tariffs lifted" OR "tariff pause" OR "trade truce" OR "free trade")',
        {"*": 0.1, "Basic Materials": 0.25, "Industrials": 0.2, "Technology": 0.2, "Consumer Cyclical": 0.25,
         "ind:Auto": 0.3, "ind:Farm": 0.3, "ind:Steel": -0.15}),
    "chip_controls": T("Chip export controls / tech restrictions",
        '("export controls" OR "chip ban" OR "chip restrictions" OR "entity list") (chips OR semiconductors OR Nvidia OR AI)',
        {"ind:Semiconductor": -0.45, "ind:Semiconductor Equipment": -0.5}),
    "shipping": T("Shipping chokepoints / freight disruption",
        '("Red Sea" OR Suez OR "Panama Canal" OR "shipping disruption" OR "freight rates" OR "port strike")',
        {"ind:Marine Shipping": 0.4, "Consumer Cyclical": -0.1, "ind:Integrated Freight": 0.1, "ind:Auto Parts": -0.1}),
    # --- Rates, growth, currency ---------------------------------------------------------
    # --- Pakistan ------------------------------------------------------------------------
    "pk_imf": T("IMF programme / reviews (Pakistan)",
        '(IMF) (Pakistan) (tranche OR review OR programme OR program OR bailout OR "staff-level")',
        {"*": 0.2, "ind:Banks": 0.1}, ["PSX"]),
    "pk_rate_cut": T("SBP rate cuts",
        '("State Bank of Pakistan" OR SBP) ("rate cut" OR "cuts policy rate" OR "cuts interest rate" OR "monetary easing")',
        {"*": 0.2, "ind:Building Materials": 0.3, "ind:Auto": 0.3, "ind:Banks": -0.2, "Real Estate": 0.2}, ["PSX"]),
    "pk_rate_hike": T("SBP rate hikes / inflation",
        '("State Bank of Pakistan" OR SBP) ("rate hike" OR "raises policy rate" OR "inflation rises" OR "inflation surges")',
        {"*": -0.2, "ind:Building Materials": -0.3, "ind:Auto": -0.3, "ind:Banks": 0.15}, ["PSX"]),
    "pk_rupee_down": T("Pakistani rupee weakening",
        '(rupee OR PKR) (falls OR depreciates OR "record low" OR slides OR weakens) (dollar OR Pakistan)',
        {"*": -0.1, "ind:Oil & Gas E&P": 0.25, "ind:Textile": 0.3, "ind:Information Technology": 0.3,
         "ind:Auto": -0.3, "ind:Oil & Gas Refining": -0.2, "ind:Drug Manufacturers": -0.2}, ["PSX"]),
    "pk_politics": T("Pakistan political unrest",
        '(Pakistan) (protest OR "political crisis" OR PTI OR "Imran Khan" OR unrest OR "no-confidence" OR "constitutional amendment")',
        {"*": -0.25}, ["PSX"]),
    "pk_india": T("India–Pakistan tensions",
        '(India Pakistan) (tensions OR strike OR border OR LoC OR military OR escalation)',
        {"*": -0.3, "ind:Aerospace": 0.1}, ["PSX"]),
    "pk_circular_debt": T("Circular-debt measures (power & energy)",
        '("circular debt") (Pakistan OR power OR gas OR settlement OR plan)',
        {"Utilities": 0.3, "ind:Oil & Gas E&P": 0.3, "ind:Oil & Gas Refining": 0.2}, ["PSX"]),
    "pk_cpec": T("CPEC / Chinese investment",
        '(CPEC OR "China-Pakistan Economic Corridor" OR "Chinese investment") Pakistan',
        {"ind:Building Materials": 0.2, "Utilities": 0.15, "ind:Steel": 0.15, "*": 0.05}, ["PSX"]),
    "pk_minerals": T("Pakistan minerals deals (Reko Diq, US/Saudi)",
        '(Pakistan) (minerals OR "Reko Diq" OR copper OR "rare earths" OR mining) (deal OR agreement OR US OR Saudi OR investment)',
        {"tk:OGDC.KA": 0.4, "tk:PPL.KA": 0.4, "ind:Oil & Gas E&P": 0.15, "*": 0.05}, ["PSX"]),
    "pk_budget_tax": T("Pakistan budget / new taxes",
        '(Pakistan) (budget OR "finance bill" OR "super tax" OR "new taxes" OR FBR)',
        {"*": -0.1, "ind:Banks": -0.15, "ind:Tobacco": -0.2}, ["PSX"]),
    "rates_down": T("Interest-rate cuts",
        '("rate cut" OR "cuts rates" OR "rate cuts" OR easing) (Fed OR RBA OR "central bank")',
        {"Real Estate": 0.5, "Utilities": 0.35, "Technology": 0.25, "Consumer Cyclical": 0.3,
         "ind:Residential Construction": 0.4, "ind:Banks": -0.2}, ["US", "ASX"]),
    "rates_up": T("Interest-rate hikes / sticky inflation",
        '("rate hike" OR "raises rates" OR "higher for longer" OR "inflation surge" OR "hot inflation") (Fed OR RBA OR "central bank")',
        {"Real Estate": -0.5, "Utilities": -0.35, "Technology": -0.3, "Consumer Cyclical": -0.3,
         "ind:Residential Construction": -0.4, "ind:Banks": 0.2, "ind:Insurance": 0.15}, ["US", "ASX"]),
    "recession": T("Recession / slowdown fears",
        '(recession OR "economic slowdown" OR "job cuts" OR "weak jobs" OR "rising unemployment") (markets OR economy)',
        {"Consumer Cyclical": -0.45, "Industrials": -0.35, "Basic Materials": -0.35, "Energy": -0.3,
         "Financial Services": -0.25, "Consumer Defensive": 0.25, "Utilities": 0.25, "Healthcare": 0.2}),
    "stimulus": T("Government spending / infrastructure / stimulus",
        '("infrastructure spending" OR "infrastructure bill" OR "stimulus package" OR "spending package" OR "tax cuts")',
        {"*": 0.05, "ind:Engineering": 0.35, "ind:Building Materials": 0.3, "ind:Steel": 0.2, "ind:Copper": 0.15,
         "ind:Railroads": 0.1, "Consumer Cyclical": 0.1}),
    "china": T("China stimulus / demand",
        '("China stimulus" OR "China demand" OR "China economy" OR "Chinese steel") (commodities OR "iron ore" OR markets)',
        {"Basic Materials": 0.5, "Energy": 0.2, "Industrials": 0.1, "ind:Luxury": 0.2}, ["US", "ASX"]),
    "aud_down": T("Australian dollar falling", '("Australian dollar" OR "Aussie dollar") (falls OR slumps OR drops OR weakens OR low)',
        {"Basic Materials": 0.2, "Energy": 0.15, "Healthcare": 0.15, "ind:Travel": -0.2, "ind:Airlines": -0.15}, ["ASX"]),
    "aud_up": T("Australian dollar rising", '("Australian dollar" OR "Aussie dollar") (rises OR jumps OR surges OR strengthens OR high)',
        {"Basic Materials": -0.15, "Energy": -0.1, "Healthcare": -0.15, "ind:Travel": 0.15, "ind:Airlines": 0.1}, ["ASX"]),
    # --- Industry policy -----------------------------------------------------------------
    "ai_capex": T("AI / data-centre spending boom",
        '("AI spending" OR "AI capex" OR "data center" OR "data centre" OR hyperscaler) (demand OR investment OR boom OR billion)',
        {"ind:Semiconductor": 0.4, "ind:Semiconductor Equipment": 0.3, "ind:Software - Infrastructure": 0.2,
         "ind:Utilities - Regulated Electric": 0.15, "ind:Copper": 0.15, "ind:Uranium": 0.2,
         "ind:REIT - Specialty": 0.2, "tk:NXT.AX": 0.4, "tk:GMG.AX": 0.2}, ["US", "ASX"]),
    "defense_spending": T("Defence spending increases",
        '("defense spending" OR "defence spending" OR "defence budget" OR "defense budget" OR "military aid" OR "NATO spending" OR AUKUS)',
        {"ind:Aerospace": 0.6}, ["US", "ASX"]),
    "drug_pricing": T("Drug-pricing / pharma policy",
        '("drug pricing" OR "drug prices" OR "most favored nation" OR "Medicare negotiation" OR "pharma tariffs" OR "pharmaceutical tariffs" OR PBS)',
        {"ind:Drug Manufacturers": -0.45, "ind:Biotechnology": -0.25, "ind:Health Care Plans": -0.1}, ["US", "ASX"]),
    "bank_regulation": T("Bank regulation / levies",
        '("bank regulation" OR "capital requirements" OR Basel OR "bank levy" OR "bank tax" OR APRA OR "stress test")',
        {"ind:Banks": -0.3, "ind:Capital Markets": -0.1}, ["US", "ASX"]),
    "deregulation": T("Deregulation (finance / energy / mining)",
        '(deregulation OR "cut red tape" OR "easing rules" OR "rollback" OR "fast-track approvals") (banks OR energy OR oil OR mining OR permits)',
        {"ind:Banks": 0.3, "Energy": 0.2, "Basic Materials": 0.15}),
    "antitrust": T("Antitrust action on Big Tech",
        '(antitrust OR monopoly OR "break up" OR DOJ OR FTC OR "competition regulator") (Google OR Apple OR Meta OR Amazon OR Microsoft OR Nvidia)',
        {"tk:GOOGL": -0.4, "tk:GOOG": -0.4, "tk:AAPL": -0.3, "tk:META": -0.3, "tk:AMZN": -0.3,
         "tk:MSFT": -0.2, "tk:NVDA": -0.2}, ["US"]),
    "mining_tax": T("Mining tax / royalty changes",
        '("mining tax" OR royalty OR royalties OR "windfall tax" OR "resource rent") (mining OR miners OR gas OR LNG)',
        {"Basic Materials": -0.3, "Energy": -0.2}, ["ASX"]),
    "housing_policy": T("Housing & property policy",
        '("housing policy" OR "first home buyer" OR "housing affordability" OR "negative gearing" OR "housing target" OR "home loan")',
        {"ind:Residential Construction": 0.25, "ind:REIT - Residential": 0.2, "Real Estate": 0.1, "ind:Building Materials": 0.15}, ["US", "ASX"]),
    "gold_haven": T("Safe-haven / central-bank gold buying",
        '("central bank gold" OR "gold buying" OR "safe haven" OR "gold demand" OR "gold reserves")',
        {"ind:Gold": 0.55}),
    # --- Shocks --------------------------------------------------------------------------
    "election": T("Elections / political uncertainty / shutdown",
        '(election OR midterms OR "government shutdown" OR "political uncertainty" OR "hung parliament") (markets OR stocks)',
        {"*": -0.1, "Healthcare": -0.1, "ind:Aerospace": 0.05}, ["US", "ASX"]),
    "pandemic": T("Disease outbreak / pandemic",
        '(outbreak OR pandemic OR epidemic OR "bird flu" OR "new virus" OR lockdown) (cases OR spread OR markets)',
        {"*": -0.1, "ind:Airlines": -0.6, "ind:Travel": -0.5, "ind:Lodging": -0.4, "ind:Resorts": -0.4,
         "ind:Diagnostics": 0.4, "Healthcare": 0.1}),
    "disasters": T("Natural disasters / extreme weather",
        '(hurricane OR cyclone OR bushfire OR wildfire OR flood OR earthquake) (damage OR insurers OR losses OR supply)',
        {"ind:Insurance": -0.35, "ind:Building Materials": 0.2, "ind:Home Improvement": 0.2, "Utilities": -0.1}),
    "food_ag": T("Farm & food shocks (drought, crop prices)",
        '(drought OR "crop prices" OR "wheat prices" OR "grain prices" OR "beef prices" OR "fertiliser prices" OR "fertilizer prices")',
        {"ind:Agricultural Inputs": 0.3, "ind:Farm": 0.1, "ind:Packaged Foods": -0.15, "ind:Grocery": -0.1}),
}


import re
_UP = r"(rise|rises|rising|jump|jumps|surge|surges|soar|soars|climb|climbs|rally|rallies|gain|gains|spike|spikes|higher|record high|stay high|firm|firms|strengthen|strengthens)"
_DN = r"(fall|falls|falling|drop|drops|slump|slumps|tumble|tumbles|slide|slides|sink|sinks|plunge|plunges|lower|retreat|retreats|slip|slips|dip|dips|ease|eases|weaken|weakens|decline|declines)"
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
    jobs = {("sector", s): f"{q} {MARKET_WORD[market]}{EXCLUDE} when:10d" for s, q in SECTOR_QUERIES.items()}
    jobs.update({("theme", k): f"{v['query']}{THEME_CONTEXT.get(market, '')}{EXCLUDE} when:10d"
                 for k, v in THEMES.items() if market in v.get("markets", [market])})
    with ThreadPoolExecutor(8) as ex:
        res = dict(zip(jobs, ex.map(lambda q: _google_news(q, market), jobs.values())))
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
    """Heat 0..1 = how unusual today's 48-hour headline count is vs that theme's own history.
    Until 5 days of history exist, themes are ranked against each other and capped at 0.45."""
    os.makedirs("results", exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame(columns=["date", "market", "theme", "n"])
    past = hist[(hist["market"] == market) & (hist["date"] != today)]
    ranks = pd.Series(counts, dtype=float).rank(pct=True) if counts else pd.Series(dtype=float)
    heat = {}
    for k, n in counts.items():
        h = past.loc[past["theme"] == k, "n"].tail(60)
        if len(h) >= 5:
            med = float(h.median())
            z = (n - med) / max(3.0, 0.5 * med)
            heat[k] = float(np.clip(0.3 + 0.35 * z, 0, 1))
        else:
            heat[k] = float(0.45 * ranks[k] ** 2) if n else 0.0  # only the busiest few matter
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


BROAD = {
    "US": ['(stocks OR "Wall Street" OR markets) when:3d', '(sanctions OR "trade deal" OR agreement OR "executive order" OR tariffs) when:3d',
           '(oil OR gold OR copper OR "rare earths" OR lithium) (deal OR supply OR prices) when:3d',
           '(Congress OR "White House" OR Pentagon OR Fed) (companies OR industry OR stocks) when:3d'],
    "PSX": ['(PSX OR KSE-100 OR "Pakistan Stock Exchange") when:3d', '(Pakistan) (IMF OR SBP OR budget OR rupee) when:3d',
            '(Pakistan) (deal OR agreement OR minerals OR China OR US OR Saudi OR army) when:3d',
            '(Pakistan) (oil OR gas OR power OR cement OR fertilizer OR textile) when:3d'],
    "ASX": ['(ASX OR "Australian shares") when:3d', '(Australia OR Canberra OR Albanese) (deal OR agreement OR policy OR tariffs) when:3d',
            '("iron ore" OR gold OR lithium OR "rare earths" OR LNG OR coal) (deal OR supply OR prices OR China) when:3d',
            '(RBA OR APRA OR ACCC OR "federal budget") when:3d'],
}


def _claude_events(market, heads, broad, universe):
    """Open-ended: Claude reads today's top business/political news and names specific events and
    which industries/stocks they move. Catches things no fixed theme list anticipates."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return []
    lines = [h["title"] for h in broad][:160]
    for (kind, name), hs in heads.items():
        lines += [h["title"] for h in hs[:5]]
    lines = list(dict.fromkeys(lines))[:260]
    prompt = (
        f"You are a buy-side macro and policy analyst covering the {market} stock market. Today's headlines:\n"
        + "\n".join("- " + x for x in lines)
        + "\n\nIdentify the 5-15 most market-relevant concrete EVENTS (e.g. a bilateral minerals deal, a regime "
        "change in an oil producer, a new sanction, a policy announcement, a major company event that ripples "
        "to its industry). Think through second-order effects (e.g. more Venezuelan oil = lower oil prices = bad "
        "for producers, good for refiners and airlines; a US minerals deal with another country may compete with "
        "Australian rare-earth producers or help them via US demand).\n"
        "For each event give the affected targets and an effect from -1 to 1 on their share prices over the "
        "next month, scaled by how big and how certain it is (most should be within ±0.4).\n"
        "Targets must be one of: 'sector:<name>', 'industry:<name>' or 'ticker:<code>' using ONLY these names.\n"
        f"Sectors: {', '.join(universe['sectors'])}\nIndustries: {', '.join(universe['industries'])}\n"
        f"Tickers: {', '.join(universe['tickers'])}\n\n"
        "Reply with only JSON: [{\"event\": short title, \"why\": one sentence, \"impacts\": "
        "[{\"target\": \"industry:Gold\", \"effect\": 0.3}]}]")
    try:
        body = json.dumps({"model": CLAUDE_MODEL, "max_tokens": 6000,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=240) as r:
            text = json.loads(r.read())["content"][0]["text"]
        evs = json.loads(text[text.index("["): text.rindex("]") + 1])
        ok = []
        for e in evs:
            imps = [i for i in e.get("impacts", []) if isinstance(i, dict) and ":" in str(i.get("target", ""))]
            for i in imps:
                i["effect"] = float(np.clip(float(i.get("effect", 0)), -1, 1))
            if imps:
                ok.append({"event": str(e.get("event", ""))[:120], "why": str(e.get("why", ""))[:300], "impacts": imps})
        print(f"[{market}] AI analyst found {len(ok)} events")
        return ok
    except Exception as e:
        print("Claude event analyst failed:", e)
        return []


def macro_context(market, demo=False, universe=None):
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
    live = {k: t for k, t in THEMES.items() if market in t.get("markets", [market])}
    def n48(hs):
        cut = (datetime.now(timezone.utc).date() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
        return sum(1 for h in hs if h.get("date", "") >= cut)
    heat = _heat(market, {k: n48(heads.get(("theme", k), [])) for k in live}) if not demo else \
        {k: min(1.0, len(heads.get(("theme", k), [])) / 10) for k in live}
    for k, t in live.items():
        hs = heads.get(("theme", k), [])
        for h in hs:
            h["score"] = round(lexicon_score(h["title"]), 2)
        themes[k] = {"label": t["label"], "heat": round(heat[k], 2), "n": len(hs), "why": None,
                     "headlines": hs[:6], "exp": t["exp"]}

    method = "wordlist"
    c = _claude(market, {k: v[:15] for k, v in heads.items()})
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
    events = []
    if universe and not demo and os.environ.get("ANTHROPIC_API_KEY"):
        with ThreadPoolExecutor(4) as ex:
            broad = [h for hs in ex.map(lambda q: _google_news(q, market), BROAD.get(market, [])) for h in hs]
        broad = sorted(broad, key=lambda x: x["ts"], reverse=True)
        events = _claude_events(market, heads, broad, universe)
    total = sum(v["n"] for v in sectors.values()) + sum(v["n"] for v in themes.values())
    print(f"[{market}] macro: {total} sector/theme headlines, scored by {method}")
    return {"sectors": sectors, "themes": themes, "events": events, "method": method, "headline_count": total}


def _matches(key, sector, industry, ticker=None):
    if key == "*":
        return True
    if key.startswith("tk:"):
        return key[3:] == ticker
    if key.startswith("ind:"):
        return isinstance(industry, str) and key[4:].lower() in industry.lower()
    return key == sector


def stock_macro(ctx, ticker, sector, industry):
    """(score -1..1, list of (theme or event label, effect)) for one stock."""
    sec = ctx["sectors"].get(sector, {}).get("score", 0.0)
    effects = []
    for k, t in ctx["themes"].items():
        e = 0.0
        for key, w in t["exp"].items():
            if _matches(key, sector, industry, ticker):
                e += w
        e *= t["heat"]
        if abs(e) >= 0.02:
            effects.append((t["label"], round(e, 2)))
    # Events found by the AI analyst (already scaled by how big/likely the impact is)
    for ev in ctx.get("events", []):
        e = 0.0
        for imp in ev.get("impacts", []):
            tgt = str(imp.get("target", ""))
            kind, _, val = tgt.partition(":")
            key = {"ticker": "tk:", "industry": "ind:"}.get(kind, "") + val if kind in ("ticker", "industry") else val
            if kind == "ticker" and val == ticker or kind != "ticker" and _matches(key, sector, industry, ticker):
                e = max(-1.0, min(1.0, e + float(imp.get("effect", 0))))
        if abs(e) >= 0.02:
            effects.append(("AI: " + ev.get("event", "event"), round(e, 2)))
    score = float(np.clip(0.5 * sec + sum(e for _, e in effects), -1, 1))
    return round(score, 3), sorted(effects, key=lambda x: -abs(x[1]))


def apply(ctx, df, fund):
    """Add macro_raw (-1..1), macro_effects and sector_news columns to df."""
    ind = fund["industry"].reindex(df.index) if "industry" in fund else pd.Series(None, index=df.index)
    res = {t: stock_macro(ctx, t, df.at[t, "sector"], ind.get(t)) for t in df.index}
    df["macro_raw"] = pd.Series({t: r[0] for t, r in res.items()})
    df["macro_effects"] = pd.Series({t: r[1] for t, r in res.items()})
    df["sector_news"] = df["sector"].map(lambda s: ctx["sectors"].get(s, {}).get("score", 0.0))
    return df
