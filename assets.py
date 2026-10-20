"""Commodities and crypto: the universes, their news, halal rules and macro settings.

They go through the same pipeline as stocks (price model, news, sector & political themes, labels),
minus everything that only exists for companies (fundamentals, financial health, dividends).
"""
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd

import diag

ASSET_MARKETS = ("COM", "CRYPTO")


def is_asset(market):
    return market in ASSET_MARKETS


# ---------------------------------------------------------------- commodities
# ticker: (name, group shown on the page, macro sector, industry words used by the theme map, news query, keywords)
# "industry" can hold several names separated by ";" — a theme exposure "ind:X" matches if X appears in it.
COMMODITIES = {
    "GC=F": ("Gold", "Precious metals", "Basic Materials", "Gold", '("gold price" OR "gold futures" OR bullion OR "spot gold")', ["gold", "bullion"]),
    "SI=F": ("Silver", "Precious metals", "Basic Materials", "Silver", '("silver price" OR "silver futures" OR "spot silver")', ["silver"]),
    "PL=F": ("Platinum", "Precious metals", "Basic Materials", "Other Precious Metals", '("platinum price" OR "platinum futures" OR platinum)', ["platinum"]),
    "PA=F": ("Palladium", "Precious metals", "Basic Materials", "Other Precious Metals", '("palladium price" OR "palladium futures" OR palladium)', ["palladium"]),
    "HG=F": ("Copper", "Industrial metals", "Basic Materials", "Copper", '("copper price" OR "copper futures" OR "LME copper" OR "Comex copper")', ["copper"]),
    "ALI=F": ("Aluminium", "Industrial metals", "Basic Materials", "Aluminum", '("aluminium price" OR "aluminum price" OR "LME aluminium" OR aluminium OR aluminum)', ["aluminium", "aluminum"]),
    "CL=F": ("Crude oil (WTI)", "Energy", "Energy", "Oil & Gas E&P;Oil & Gas Integrated", '("oil prices" OR "crude oil" OR WTI OR "oil futures")', ["oil", "crude", "wti"]),
    "BZ=F": ("Brent crude", "Energy", "Energy", "Oil & Gas E&P;Oil & Gas Integrated", '("Brent crude" OR "Brent oil" OR "oil prices")', ["brent", "oil", "crude"]),
    "NG=F": ("Natural gas", "Energy", "Energy", "Oil & Gas E&P;Natural Gas;LNG", '("natural gas prices" OR "natural gas futures" OR "Henry Hub" OR LNG)', ["natural gas", "lng", "henry hub", "gas prices"]),
    "RB=F": ("Gasoline", "Energy", "Energy", "Oil & Gas E&P;Gasoline", '("gasoline futures" OR "gasoline prices" OR "RBOB")', ["gasoline", "rbob", "petrol"]),
    "HO=F": ("Heating oil / diesel", "Energy", "Energy", "Oil & Gas E&P;Diesel", '("heating oil" OR "diesel prices" OR "diesel futures" OR "ULSD")', ["heating oil", "diesel", "ulsd"]),
    "URA": ("Uranium (URA miners ETF)", "Battery & nuclear", "Energy", "Uranium", '(uranium price OR "uranium market" OR "nuclear fuel")', ["uranium", "nuclear"]),
    "LIT": ("Lithium (LIT miners ETF)", "Battery & nuclear", "Basic Materials", "Lithium;Other Industrial Metals", '("lithium price" OR "lithium market" OR "lithium prices" OR "battery metals")', ["lithium", "battery"]),
    "ZW=F": ("Wheat", "Grains", "Agriculture", "Farm Products;Grains", '("wheat prices" OR "wheat futures" OR "wheat crop" OR "wheat exports")', ["wheat"]),
    "ZC=F": ("Corn", "Grains", "Agriculture", "Farm Products;Grains", '("corn prices" OR "corn futures" OR "corn crop" OR maize)', ["corn", "maize"]),
    "ZS=F": ("Soybeans", "Grains", "Agriculture", "Farm Products;Grains", '("soybean prices" OR "soybean futures" OR soybeans OR "soy exports")', ["soybean", "soy"]),
    "KC=F": ("Coffee", "Softs", "Agriculture", "Farm Products;Softs", '("coffee prices" OR "coffee futures" OR arabica OR robusta)', ["coffee", "arabica", "robusta"]),
    "SB=F": ("Sugar", "Softs", "Agriculture", "Farm Products;Softs", '("sugar prices" OR "sugar futures" OR "raw sugar")', ["sugar"]),
    "CC=F": ("Cocoa", "Softs", "Agriculture", "Farm Products;Softs", '("cocoa prices" OR "cocoa futures" OR cocoa)', ["cocoa"]),
    "CT=F": ("Cotton", "Softs", "Agriculture", "Farm Products;Softs", '("cotton prices" OR "cotton futures" OR "cotton crop")', ["cotton"]),
    "LE=F": ("Live cattle", "Livestock", "Agriculture", "Farm Products;Livestock;Beef", '("cattle prices" OR "cattle futures" OR "beef prices" OR "live cattle")', ["cattle", "beef"]),
}

# ---------------------------------------------------------------- crypto
CRYPTO_CACHE = "results/universe_CRYPTO.csv"
# Stablecoins, wrapped/staked/bridged copies and exchange IOUs don't move on their own — left out
_SKIP_ID = re.compile(r"(wrapped|staked|bridged|-usd|usd-|tether|usdc|dai$|^dai|stasis|paxos|gold-token|tether-gold|"
                      r"pax-gold|binance-peg|liquid-staking|restaked|weth|steth|msol|jitosol|cbbtc|ethena|usds|"
                      r"first-digital|true-usd|frax|paypal|ripple-usd|global-dollar|blackrock-usd|usd1|susds)", re.I)
_SKIP_SYM = {"USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDS", "PYUSD", "USDD", "BUSD", "USD0", "RLUSD", "USD1",
             "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "CBBTC", "RETH", "METH", "BSC-USD", "XAUT", "PAXG", "BUIDL",
             "SUSDS", "SUSDE", "USDX", "GHO", "LBTC", "SOLVBTC", "JITOSOL", "BNSOL"}
# Yahoo uses a numbered code for a few coins whose symbol clashes with another listing
YAHOO_ALIAS = {"UNI": "UNI7083-USD", "SUI": "SUI20947-USD", "APT": "APT21794-USD", "TON": "TON11419-USD",
               "PEPE": "PEPE24478-USD", "TAO": "TAO22974-USD", "HBAR": "HBAR-USD", "ARB": "ARB11841-USD",
               "OP": "OP-USD", "STX": "STX4847-USD", "IMX": "IMX10603-USD", "INJ": "INJ-USD", "GRT": "GRT6719-USD",
               "MNT": "MNT27075-USD", "WIF": "WIF-USD", "BONK": "BONK-USD", "RENDER": "RENDER-USD",
               "ENA": "ENA-USD", "ONDO": "ONDO-USD", "HYPE": "HYPE32196-USD", "TRUMP": "TRUMP35336-USD",
               "S": "S32684-USD", "KAS": "KAS-USD", "POL": "POL28321-USD"}
CRYPTO_FALLBACK = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "TRX", "ADA", "HYPE", "LINK", "XLM", "BCH", "SUI", "AVAX",
                   "LTC", "HBAR", "TON", "SHIB", "DOT", "XMR", "UNI", "CRO", "AAVE", "PEPE", "NEAR", "APT", "ETC", "ICP",
                   "ONDO", "TAO", "POL", "ARB", "KAS", "ATOM", "ALGO", "RENDER", "FIL", "VET", "OP", "ENA", "SEI",
                   "INJ", "IMX", "STX", "GRT", "BONK", "WIF", "TIA", "FET", "JUP", "MKR", "QNT"]
# Rough groups, for "peers" and the macro map
_GROUPS = {
    "Store of value": {"BTC", "BCH", "LTC", "XMR", "KAS", "ETC", "ZEC", "DASH", "BSV"},
    "Smart-contract platforms": {"ETH", "SOL", "BNB", "ADA", "AVAX", "TRX", "DOT", "NEAR", "APT", "SUI", "TON", "ICP",
                                 "ATOM", "ALGO", "HBAR", "SEI", "INJ", "TIA", "EGLD", "XTZ", "FTM", "S", "HYPE", "VET", "EOS"},
    "Layer-2 / scaling": {"POL", "MATIC", "ARB", "OP", "IMX", "STX", "MNT", "STRK", "ZK"},
    "Payments": {"XRP", "XLM", "CRO", "BCH", "LTC", "XDC"},
    "DeFi": {"UNI", "AAVE", "MKR", "LINK", "ONDO", "JUP", "ENA", "LDO", "CRV", "COMP", "SNX", "PENDLE", "RUNE", "CAKE",
             "DYDX", "GMX", "SKY", "QNT", "GRT"},
    "AI & data": {"TAO", "FET", "RENDER", "GRT", "FIL", "AR", "VIRTUAL", "WLD", "AKT"},
    "Meme coins": {"DOGE", "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "TRUMP", "PENGU", "SPX", "FARTCOIN", "BRETT", "POPCAT"},
}
_LENDING = {"AAVE", "COMP", "MKR", "SKY", "ENA", "PENDLE", "CRV", "SNX", "JST", "MORPHO", "LQTY", "XVS", "CAKE", "GMX", "DYDX"}


def _group(sym):
    for g, s in _GROUPS.items():
        if sym in s:
            return g
    return "Other crypto"


def crypto_universe(n=50):
    """Top-n coins by market cap from CoinGecko (free, no key), minus stablecoins and wrapped tokens.
    Returns DataFrame indexed by Yahoo ticker: name, symbol, sector (group), mcap."""
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=150&page=1"
    rows = []
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "stock-screener", "Accept": "application/json"})
            data = json.loads(urllib.request.urlopen(req, timeout=30).read())
            for c in data:
                sym, cid = str(c.get("symbol", "")).upper(), str(c.get("id", ""))
                if sym in _SKIP_SYM or _SKIP_ID.search(cid) or "USD" in sym:
                    continue
                px = c.get("current_price") or 0
                if 0.97 <= px <= 1.03 and abs(c.get("price_change_percentage_24h") or 0) < 0.5:
                    continue   # behaves like a stablecoin
                rows.append({"ticker": YAHOO_ALIAS.get(sym, f"{sym}-USD"), "symbol": sym, "name": c.get("name"),
                             "mcap": c.get("market_cap"), "cg_id": cid, "cg_price": px})
                if len(rows) >= n:
                    break
            break
        except Exception as e:
            print(f"WARNING CoinGecko attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (attempt + 1))
    if rows:
        df = pd.DataFrame(rows).drop_duplicates("ticker").set_index("ticker")
        os.makedirs("results", exist_ok=True)
        df.to_csv(CRYPTO_CACHE)
        diag.put("universe", source="live", count=len(df))
    elif os.path.exists(CRYPTO_CACHE):
        df = pd.read_csv(CRYPTO_CACHE, index_col=0).drop(columns=["cg_price"], errors="ignore")  # stale prices
        diag.put("universe", source="saved list", count=len(df))
    else:
        df = pd.DataFrame({"symbol": CRYPTO_FALLBACK, "name": CRYPTO_FALLBACK, "mcap": None},
                          index=pd.Index([YAHOO_ALIAS.get(s, f"{s}-USD") for s in CRYPTO_FALLBACK], name="ticker"))
        diag.put("universe", source="built-in fallback", count=len(df))
    df["sector"] = df["symbol"].map(_group)
    return df


def check_tickers(uni, close):
    """Yahoo sometimes has a different coin under the same symbol. Drop any whose price is far from
    CoinGecko's (more than ~35% apart) — that's the wrong coin, not a price move."""
    if "cg_price" not in uni or not len(close):
        return close, []
    last = close.ffill().iloc[-1]
    bad = []
    for t in close.columns:
        cg = pd.to_numeric(uni["cg_price"].get(t), errors="coerce") if t in uni.index else None
        if cg and cg > 0 and pd.notna(last.get(t)) and not (0.65 <= last[t] / cg <= 1.5):
            bad.append(f"{t} (Yahoo {last[t]:.6g} vs CoinGecko {cg:.6g})")
    if bad:
        print("WARNING [CRYPTO] wrong coin on Yahoo for:", "; ".join(bad))
        diag.put("prices", wrong_coin=bad[:20])
    return close[[t for t in close.columns if not any(b.startswith(t + " ") for b in bad)]], bad


def universe(market):
    """DataFrame indexed by ticker: name, sector (group shown on the page), macro_sector, industry, mcap,
    news query and keywords."""
    if market == "COM":
        df = pd.DataFrame([{"ticker": t, "name": v[0], "sector": v[1], "macro_sector": v[2], "industry": v[3],
                            "q": v[4], "kw": v[5], "mcap": None, "symbol": t} for t, v in COMMODITIES.items()]).set_index("ticker")
        diag.put("universe", source="built-in list", count=len(df))
        return df
    df = crypto_universe()
    df["macro_sector"] = "Crypto"
    df["industry"] = df["sector"]
    df["q"] = [f'("{n}" OR {s}) (crypto OR token OR coin OR price)' if len(s) >= 3 and s.isalpha() else f'"{n}" (crypto OR token OR coin)'
               for n, s in zip(df["name"], df["symbol"])]
    df["kw"] = [[str(n).lower()] + ([s.lower()] if len(s) >= 3 else []) for n, s in zip(df["name"], df["symbol"])]
    return df


def fundamentals_frame(uni, close):
    """A 'fund' table with the same columns as for stocks (mostly empty)."""
    from data import FUND_FIELDS
    fund = pd.DataFrame(index=pd.Index(close.columns, name="ticker"), columns=FUND_FIELDS, dtype=object)
    u = uni.reindex(fund.index)
    fund["shortName"] = u["name"]
    fund["longName"] = u["name"]
    fund["sector"] = u["sector"]
    fund["industry"] = u["industry"]
    fund["macro_sector"] = u["macro_sector"]
    fund["marketCap"] = pd.to_numeric(u["mcap"], errors="coerce")
    fund["currency"] = "USD"
    return fund


# ---------------------------------------------------------------- news
ASSET_SITES = {
    "COM": ["reuters.com", "bloomberg.com", "cnbc.com", "ft.com", "wsj.com", "marketwatch.com", "kitco.com",
            "mining.com", "oilprice.com", "agriculture.com", "barchart.com", "spglobal.com"],
    "CRYPTO": ["coindesk.com", "theblock.co", "decrypt.co", "cointelegraph.com", "reuters.com", "bloomberg.com",
               "cnbc.com", "ft.com", "dlnews.com", "blockworks.co"],
}


def _asset_news(args):
    t, q, kws, market = args
    from data import LOW_QUALITY, _google_news, quality_of
    now = datetime.now(timezone.utc)
    sites = " OR ".join(f"site:{d}" for d in ASSET_SITES[market])
    items = _google_news(f"{q} ({sites}) when:10d", "US") + _google_news(f"{q} when:7d", "US")
    seen, out, promo = set(), [], 0
    for i in sorted(items, key=lambda x: x["ts"], reverse=True):
        key = i["title"].lower()[:60]
        tl = i["title"].lower()
        if (now - i["ts"]).days > 10 or key in seen:
            continue
        if (i["publisher"] or "").lower() in LOW_QUALITY:
            diag.inc("news", "dropped_lowq")
            continue
        if not any(re.search(r"\b" + re.escape(k) + r"\b", tl) for k in kws):
            diag.inc("news", "dropped_irrelevant")
            continue
        qual = quality_of(i["publisher"])
        if qual == "promo":
            if promo >= 3:
                continue
            promo += 1
        seen.add(key)
        out.append({"title": i["title"], "link": i["link"], "publisher": i["publisher"],
                    "date": i["ts"].strftime("%Y-%m-%d"), "quality": qual})
    out.sort(key=lambda h: h["date"], reverse=True)
    out.sort(key=lambda h: h["quality"] == "promo")
    return t, out[:15]


def get_news(uni, tickers, market):
    with ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(_asset_news, [(t, uni.at[t, "q"], uni.at[t, "kw"], market) for t in tickers if t in uni.index]))
    n = sum(1 for v in res.values() if v)
    print(f"[{market}] news: {n}/{len(res)} with headlines")
    diag.put("news", coverage=round(n / max(1, len(res)), 2), items=sum(len(v) for v in res.values()))
    return res


# ---------------------------------------------------------------- halal (simple rules)
def halal(market, ticker, row):
    """Same shape as halal.screen(): {status, method, reasons, ratios}."""
    if market == "COM":
        grp = row.get("sector")
        if grp == "Precious metals":
            return {"status": "HALAL", "method": "ASSET", "ratios": {},
                    "reasons": ["Gold and silver may be owned when bought spot — hand-to-hand, paid in full, with "
                                "physical delivery or a fully bullion-backed, Shariah-certified product.",
                                "Futures, options, leveraged or unallocated products on it are NOT permissible."]}
        if "ETF" in str(row.get("name")):
            return {"status": "DOUBTFUL", "method": "ASSET", "ratios": {},
                    "reasons": ["This tracks a fund of mining companies — screen the fund's holdings, or use a "
                                "Shariah-certified fund instead."]}
        return {"status": "DOUBTFUL", "method": "ASSET", "ratios": {},
                "reasons": ["The commodity itself is permissible to own and trade physically.",
                            "Retail access is usually through futures or futures-based ETFs, which most scholars "
                            "don't permit — only a physically-backed or Shariah-certified product would be halal."]}
    sym = str(row.get("symbol") or ticker.split("-")[0]).upper()
    if sym in _LENDING:
        return {"status": "NOT HALAL", "method": "ASSET", "ratios": {},
                "reasons": ["A lending / interest-yield (DeFi) token — its value comes from interest-based "
                            "lending (riba)."]}
    if row.get("sector") == "Meme coins":
        return {"status": "DOUBTFUL", "method": "ASSET", "ratios": {},
                "reasons": ["Meme coin with no underlying use — many scholars consider it excessive speculation "
                            "(gharar / maysir) and advise against it."]}
    return {"status": "DOUBTFUL", "method": "ASSET", "ratios": {},
            "reasons": ["Scholars differ on cryptocurrency: some permit major coins with real use as digital "
                        "assets, others don't. Check a Shariah screening service for this coin.",
                        "Margin, futures and lending/staking for interest are not permissible either way."]}


# ---------------------------------------------------------------- macro settings for these markets
SECTOR_QUERIES = {
    "COM": {
        "Energy": '("oil prices" OR crude OR OPEC OR "natural gas prices" OR LNG OR gasoline)',
        "Basic Materials": '("gold price" OR "silver price" OR "copper price" OR "metals prices" OR aluminium OR lithium OR uranium)',
        "Agriculture": '("grain prices" OR "wheat prices" OR "corn prices" OR soybeans OR "coffee prices" OR "cocoa prices" OR "sugar prices" OR "cattle prices")',
    },
    "CRYPTO": {
        "Crypto": '(bitcoin OR ethereum OR crypto OR cryptocurrency OR "digital assets")',
    },
}
MARKET_LABEL = {"COM": "commodities (futures) market", "CRYPTO": "cryptocurrency market"}
# Existing stock-market themes that also move these markets
SHARED_THEMES = {
    "COM": ["war", "ceasefire", "china_tensions", "critical_minerals", "sanctions", "oil_supply_down", "oil_supply_up",
            "drilling_policy", "climate_policy", "tariffs", "trade_deal", "shipping", "recession", "stimulus", "china",
            "gold_haven", "disasters", "food_ag", "ai_capex"],
    "CRYPTO": ["war", "ceasefire", "tariffs", "trade_deal", "recession", "stimulus", "election"],
}
BROAD = {
    "COM": ['(commodities OR "commodity prices") when:3d', '(OPEC OR "oil market" OR "oil supply") when:3d',
            '(gold OR silver OR copper) (prices OR demand OR supply) when:3d',
            '(wheat OR corn OR soybeans OR coffee OR cocoa OR sugar OR cattle) (prices OR harvest OR exports) when:3d'],
    "CRYPTO": ['(bitcoin OR crypto) when:3d', '(SEC OR regulation OR "stablecoin bill" OR "crypto bill") crypto when:3d',
               '("bitcoin ETF" OR "ether ETF" OR "crypto ETF") when:3d', '(Fed OR "rate cut" OR inflation) (bitcoin OR crypto) when:3d'],
}


def extra_themes(T):
    """Themes specific to commodities and crypto (same format as macro.THEMES)."""
    return {
        # --- commodities ---
        "usd_strong": T("US dollar strengthening",
            '("US dollar" OR "dollar index" OR DXY OR greenback) (rallies OR strengthens OR surges OR jumps OR "multi-month high")',
            {"*": -0.2, "ind:Gold": -0.15, "ind:Silver": -0.15}, ["COM", "CRYPTO"]),
        "usd_weak": T("US dollar weakening",
            '("US dollar" OR "dollar index" OR DXY OR greenback) (falls OR weakens OR slides OR slumps OR "multi-month low")',
            {"*": 0.2, "ind:Gold": 0.15, "ind:Silver": 0.15}, ["COM", "CRYPTO"]),
        "fed_cut_assets": T("Fed rate cuts / easier money",
            '(Fed OR "Federal Reserve" OR Powell) ("rate cut" OR "cuts rates" OR dovish OR easing)',
            {"ind:Gold": 0.35, "ind:Silver": 0.3, "Crypto": 0.35, "Basic Materials": 0.1}, ["COM", "CRYPTO"]),
        "fed_hike_assets": T("Fed hawkish / higher for longer",
            '(Fed OR "Federal Reserve" OR Powell) (hawkish OR "rate hike" OR "higher for longer" OR "hot inflation")',
            {"ind:Gold": -0.3, "ind:Silver": -0.25, "Crypto": -0.35, "Basic Materials": -0.1}, ["COM", "CRYPTO"]),
        "crop_shock": T("Bad weather / crop failures",
            '(drought OR frost OR "crop failure" OR "poor harvest" OR "El Nino" OR "La Nina" OR "heat wave" OR floods) '
            '(wheat OR corn OR soybeans OR coffee OR cocoa OR sugar OR crops OR harvest)',
            {"ind:Grains": 0.4, "ind:Softs": 0.45}, ["COM"]),
        "crop_glut": T("Bumper harvests / ample supply",
            '("record harvest" OR "bumper crop" OR "record crop" OR "ample supply" OR "supply glut") '
            '(wheat OR corn OR soybeans OR coffee OR cocoa OR sugar OR cotton)',
            {"ind:Grains": -0.4, "ind:Softs": -0.4}, ["COM"]),
        "nuclear_push": T("Nuclear power expansion",
            '("nuclear power" OR "nuclear reactors" OR "small modular reactor" OR SMR) (plan OR approval OR deal OR build)',
            {"ind:Uranium": 0.5}, ["COM"]),
        "ev_demand": T("EV & battery demand",
            '("EV sales" OR "electric vehicle sales" OR "battery demand" OR "battery storage") (growth OR record OR slowdown)',
            {"ind:Lithium": 0.4, "ind:Copper": 0.15}, ["COM"]),
        # --- crypto ---
        "crypto_etf_in": T("Crypto ETF inflows / approvals",
            '("bitcoin ETF" OR "ether ETF" OR "crypto ETF" OR "spot ETF") (inflows OR approval OR approved OR record OR launch)',
            {"Crypto": 0.5}, ["CRYPTO"]),
        "crypto_etf_out": T("Crypto ETF outflows",
            '("bitcoin ETF" OR "ether ETF" OR "crypto ETF") (outflows OR redemptions OR "pull money")',
            {"Crypto": -0.45}, ["CRYPTO"]),
        "crypto_policy_good": T("Pro-crypto policy (clear rules, reserves)",
            '(crypto OR bitcoin OR stablecoin) ("bill passes" OR "signed into law" OR "regulatory clarity" OR '
            '"strategic reserve" OR "market structure bill" OR legalise OR legalize OR "dismisses case")',
            {"Crypto": 0.45}, ["CRYPTO"]),
        "crypto_crackdown": T("Crypto crackdown / lawsuits / bans",
            '(crypto OR bitcoin OR exchange) (crackdown OR ban OR banned OR "SEC sues" OR lawsuit OR "enforcement action" OR charges)',
            {"Crypto": -0.45}, ["CRYPTO"]),
        "crypto_hack": T("Hacks / exchange failures",
            '(crypto OR exchange OR DeFi OR bridge) (hack OR hacked OR exploit OR "funds stolen" OR insolvency OR "halts withdrawals")',
            {"Crypto": -0.4, "ind:DeFi": -0.2}, ["CRYPTO"]),
        "crypto_corporate": T("Companies / institutions buying crypto",
            '("bitcoin treasury" OR "buys bitcoin" OR "adds bitcoin" OR "institutional adoption" OR "bank to offer crypto")',
            {"Crypto": 0.35, "ind:Store of value": 0.15}, ["CRYPTO"]),
    }
