"""Synthetic data so the pipeline can be tested without internet."""
import numpy as np
import pandas as pd


def fake_market(tickers, index_name, days=1000, seed=0):
    rng = np.random.default_rng(seed + len(tickers))
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    mkt = rng.normal(0.0004, 0.01, days)
    idx = pd.Series(100 * np.exp(np.cumsum(mkt)), index=dates, name=index_name)
    drift = rng.normal(0, 0.0004, len(tickers))
    rets = mkt[:, None] * rng.uniform(0.6, 1.4, len(tickers)) + drift + rng.normal(0, 0.015, (days, len(tickers)))
    close = pd.DataFrame(50 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=tickers)
    volume = pd.DataFrame(rng.lognormal(14, 0.4, (days, len(tickers))), index=dates, columns=tickers)
    sectors = rng.choice(["Technology", "Financial Services", "Energy", "Healthcare", "Materials"], len(tickers))
    fund = pd.DataFrame({
        "shortName": [f"{t} Corp" for t in tickers], "sector": sectors, "industry": sectors,
        "currency": "USD", "marketCap": rng.uniform(2e9, 2e12, len(tickers)),
        "trailingPE": rng.uniform(5, 60, len(tickers)), "forwardPE": rng.uniform(5, 50, len(tickers)),
        "priceToBook": rng.uniform(1, 15, len(tickers)), "profitMargins": rng.uniform(-0.05, 0.4, len(tickers)),
        "revenueGrowth": rng.normal(0.08, 0.1, len(tickers)), "earningsGrowth": rng.normal(0.1, 0.2, len(tickers)),
        "debtToEquity": rng.uniform(0, 200, len(tickers)), "returnOnEquity": rng.uniform(0, 0.4, len(tickers)),
        "freeCashflow": rng.uniform(-1e9, 5e10, len(tickers)), "dividendYield": rng.uniform(0, 5, len(tickers)),
        "recommendationKey": "buy", "targetMeanPrice": 100.0,
    }, index=pd.Index(tickers, name="ticker"))
    heads = ["{t} beats estimates and raises guidance", "{t} shares fall on weak outlook",
             "{t} faces new tariff risk as China policy shifts", "{t} announces buyback",
             "Analyst downgrade hits {t}", "{t} signs major contract"]
    news = {t: [h.format(t=t) for h in rng.choice(heads, rng.integers(0, 5))] for t in tickers}
    return close, volume, idx, fund, news
