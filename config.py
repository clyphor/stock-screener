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

MARKETS = {
    "US":  {"tickers": US_TICKERS,  "index": "SPY",   "min_dollar_vol": 20e6, "min_mcap": 5e9},
    "ASX": {"tickers": ASX_TICKERS, "index": "^AXJO", "min_dollar_vol": 5e6,  "min_mcap": 1e9},
}

# ---- Model -----------------------------------------------------------------
HORIZON_DAYS = 21          # predict ~1 month ahead return vs the index
HISTORY = "4y"             # price history to download
TEST_DAYS = 126            # last ~6 months held out for the honest backtest

# How the final score blends the parts (must sum to 1)
WEIGHTS = {
    "ml": 0.45,           # LightGBM on technical features
    "fundamental": 0.30,  # value + quality + growth vs peers
    "news": 0.15,         # company news sentiment
    "peers": 0.10,        # competitor / sector news sentiment
}

# Used instead when the price model fails its backtest in a market (IC below this)
MIN_MODEL_IC = 0.02
WEIGHTS_NO_MODEL = {"ml": 0.10, "fundamental": 0.50, "news": 0.25, "peers": 0.15}

TOP_N = 20                # how many picks to show per market

# Optional: set ANTHROPIC_API_KEY as a GitHub secret to score news with Claude
# instead of the built-in word list.
CLAUDE_MODEL = "claude-haiku-5-5"
