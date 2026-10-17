"""Settings you can edit. Ask Claude to change anything here."""

# ---- Universes -------------------------------------------------------------
US_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "BRK-B", "JPM",
    "LLY", "V", "UNH", "XOM", "MA", "JNJ", "PG", "HD", "COST", "ABBV",
    "MRK", "CVX", "ORCL", "CRM", "BAC", "KO", "PEP", "AMD", "NFLX", "TMO",
    "ADBE", "WMT", "MCD", "CSCO", "ACN", "LIN", "ABT", "DHR", "INTC", "QCOM",
    "TXN", "WFC", "DIS", "CAT", "AMGN", "IBM", "INTU", "GE", "PFE", "NOW",
    "UNP", "GS", "MS", "BA", "HON", "LOW", "SPGI", "RTX", "BKNG", "ISRG",
    "UBER", "PLTR", "MU", "AMAT", "LRCX", "PANW", "DE", "LMT", "NKE", "SBUX",
    "CVS", "COP", "SLB", "NEE", "DUK", "SO", "PLD", "AMT", "T", "VZ",
]

ASX_TICKERS = [
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX", "MQG.AX",
    "FMG.AX", "WDS.AX", "TLS.AX", "RIO.AX", "GMG.AX", "WOW.AX", "TCL.AX", "ALL.AX",
    "QBE.AX", "STO.AX", "COL.AX", "SUN.AX", "REA.AX", "XRO.AX", "WTC.AX", "NST.AX",
    "S32.AX", "IAG.AX", "ORG.AX", "SHL.AX", "JHX.AX", "MIN.AX", "PLS.AX", "RMD.AX",
    "CPU.AX", "ASX.AX", "AMC.AX", "SCG.AX", "TWE.AX", "QAN.AX", "EVN.AX", "NXT.AX",
    "CAR.AX", "SEK.AX", "APA.AX", "AGL.AX", "MPL.AX", "BXB.AX", "LYC.AX", "TPG.AX",
    "IGO.AX", "SGP.AX",
]

PSX_TICKERS = ["OGDC.KA", "PPL.KA", "MARI.KA", "LUCK.KA", "MCB.KA", "UBL.KA", "HBL.KA", "ENGRO.KA",
               "FFC.KA", "EFERT.KA", "PSO.KA", "SYS.KA", "MEBL.KA", "BAHL.KA", "POL.KA", "DGKC.KA"]

MARKETS = {
    "US":  {"tickers": US_TICKERS,  "index": "SPY", "index_candidates": ["SPY", "^GSPC", "IVV"],   "min_dollar_vol": 20e6, "min_mcap": 5e9},
    "ASX": {"tickers": ASX_TICKERS, "index": "^AXJO", "index_candidates": ["^AXJO", "STW.AX", "IOZ.AX"], "min_dollar_vol": 5e6,  "min_mcap": 1e9},
    # Pakistan: KSE-100. Prices in PKR. No index feed, so an equal-weighted index is built from members.
    "PSX": {"tickers": PSX_TICKERS, "index": "KSE100 (built)", "index_candidates": [], "min_dollar_vol": 20e6,
            "min_mcap": 5e9, "currency": "PKR"},
}

# When each market's daily run happens (UTC) — after its close, once all data sources have the day.
# US 05:30 UTC: Massive's free plan has the previous US session from midnight New York time.
# ASX 08:15 UTC: ~2 hours after the Sydney close. PSX 12:45 UTC: ~2 hours after the Karachi close.
# (Keep in sync with the cron lines in .github/workflows/daily.yml.)
SCHEDULE = {"US": ("30 5 * * 2-6", 5, 30, (1, 2, 3, 4, 5)),    # cron, hour, minute, UTC weekdays (Mon=0)
            "ASX": ("15 8 * * 1-5", 8, 15, (0, 1, 2, 3, 4)),
            "PSX": ("45 12 * * 1-5", 12, 45, (0, 1, 2, 3, 4))}
SITE = "https://clyphor.github.io/stock-screener/"

# ---- Model -----------------------------------------------------------------
HORIZON_DAYS = 21          # predict ~1 month ahead return vs the index
HISTORY = "6y"             # price history to download (6y so 5-year performance can be shown)
TEST_DAYS = 126            # last ~6 months held out for the honest backtest

# How the final score blends the parts (must sum to 1)
WEIGHTS = {
    "ml": 0.40,           # LightGBM on technical features
    "fundamental": 0.28,  # value + quality + growth vs peers
    "news": 0.12,         # company news sentiment
    "peers": 0.08,        # competitors' news sentiment
    "macro": 0.12,        # sector news (oil, iron ore, rates…) + political themes (war, tariffs, elections…)
}

# Used instead when the price model fails its backtest in a market (IC below this)
MIN_MODEL_IC = 0.02
WEIGHTS_NO_MODEL = {"ml": 0.10, "fundamental": 0.45, "news": 0.17, "peers": 0.10, "macro": 0.18}

# Bump this whenever the scoring/label rules change, so label changes caused by a rules update are
# recorded as "rules updated" rather than looking like the market moved.
SCORING_VERSION = 7

TOP_N = 20                # how many picks to show per market

# Optional: set ANTHROPIC_API_KEY as a GitHub secret to score news with Claude
# instead of the built-in word list.
CLAUDE_MODEL = "claude-haiku-5-5"


# ---- Database for watchlists & paper trades (Supabase) -------------------------
# The URL and the *anon/publishable* key are meant to be public (they sit in the web page);
# row-level security in db/schema.sql keeps each user's data private.
SUPABASE_URL = "https://eqwcuyfqaytdrravkaaw.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_MfqpFg_wuKzO1EN5NQW69w_SopvIz8l"  # publishable key: safe in the page
