"""Daily exchange rates for the page (docs/fx.json), so prices and paper-trade profits can also be shown in
the viewer's main currency. Rates are units of each currency per 1 US dollar, from Yahoo Finance.
Three years of daily history, so a paper trade is converted at the rate of the day it was bought/sold."""
import json
import os

import pandas as pd
import yfinance as yf

import diag

CURRENCIES = ["AUD", "PKR", "EUR", "GBP", "CAD", "NZD", "INR", "AED", "SAR", "SGD", "JPY", "CNY", "HKD", "MYR"]
PATH = "docs/fx.json"


def update(period="3y"):
    try:
        raw = yf.download([f"{c}=X" for c in CURRENCIES], period=period, interval="1d", auto_adjust=False,
                          progress=False, threads=True)
        px = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        px.columns = [str(c).replace("=X", "") for c in px.columns]
        px = px.sort_index().ffill().dropna(how="all")
        px = px[[c for c in CURRENCIES if c in px.columns]]
        # a rate that jumps >25% in a day is a bad print — drop it and carry the previous day
        bad = (px / px.shift(1) - 1).abs() > 0.25
        px = px.mask(bad).ffill()
        if px.empty or len(px.columns) < len(CURRENCIES) // 2:
            raise ValueError(f"only {len(px.columns)} currencies returned")
        out = {"updated": px.index[-1].strftime("%Y-%m-%d"),
               "dates": [d.strftime("%Y-%m-%d") for d in px.index],
               "rates": {"USD": [1.0] * len(px)}}
        for c in px.columns:
            out["rates"][c] = [None if v != v else float(f"{v:.6g}") for v in px[c]]
        os.makedirs("docs", exist_ok=True)
        with open(PATH, "w") as f:
            json.dump(out, f, separators=(",", ":"))
        latest = {c: out["rates"][c][-1] for c in out["rates"]}
        print(f"exchange rates up to {out['updated']}: AUD {latest.get('AUD')} PKR {latest.get('PKR')} per USD")
        diag.put("fx", updated=out["updated"], currencies=len(out["rates"]), market="general")
        return latest
    except Exception as e:
        # keep yesterday's file (it is copied in from the live page) rather than publishing nothing
        print("WARNING exchange rates not updated:", e)
        diag.sample("fx", "errors", str(e)[:150], market="general")
        return None
