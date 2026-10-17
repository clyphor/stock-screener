"""Second price source, used to verify Yahoo's latest closes and fill a missing latest day.

PSX: the exchange's own company pages (already read for fundamentals) — official, free, latest day only.
US:  Massive (formerly Polygon) "grouped daily" — one call returns every US stock's day bar.
     Free key; only used when the MASSIVE_API_KEY secret is set.
ASX: no free second source — Yahoo only.

Where the two disagree by more than TOL, the official / second source is used and the stock is counted
as "corrected". Everything is logged in the run log under "Price check".
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

import diag

TOL = 0.015          # 1.5% difference counts as a disagreement
MIN_COVER = 0.6      # a new day is only added if the second source has it for this share of stocks


def _apply(name, close, volume, other, other_vol, day, source):
    """other: {ticker: close} from the second source for `day`. Returns (close, volume)."""
    other = {t: v for t, v in other.items() if t in close.columns and v and v > 0}
    if not other:
        return close, volume
    day = pd.Timestamp(day)
    last = close.index[-1]
    if day > last:  # Yahoo is missing this day — add it if the second source covers enough stocks
        cover = len(other) / max(1, close.shape[1])
        if cover < MIN_COVER:
            print(f"[{name}] price check: {source} has {day.date()} for only {cover:.0%} of stocks — not added")
            diag.put("pricecheck", market=name, source=source, skipped_day=str(day.date()), cover=round(cover, 2))
            return close, volume
        close.loc[day] = pd.Series(other)
        volume.loc[day] = pd.Series(other_vol)
        close, volume = close.sort_index(), volume.sort_index()
        # stocks the second source lacks: carry their last close into the new day (no fake gap)
        close.loc[day] = close.loc[day].fillna(close.loc[:day].iloc[-2])
        volume.loc[day] = volume.loc[day].fillna(0)
        print(f"[{name}] price check: added {day.date()} from {source} ({len(other)} stocks) — Yahoo didn't have it yet")
        diag.put("pricecheck", market=name, source=source, added_day=str(day.date()), added_stocks=len(other))
        return close, volume
    if day not in close.index:
        return close, volume
    y = close.loc[day]
    agree, fixed, filled = 0, [], 0
    for t, v in other.items():
        yv = y.get(t)
        if yv is None or yv != yv:
            close.loc[day, t] = v
            filled += 1
        elif abs(yv / v - 1) <= TOL:
            agree += 1
        else:
            fixed.append(f"{t} {yv:.2f}→{v:.2f}")
            close.loc[day, t] = v
    print(f"[{name}] price check vs {source} on {day.date()}: {agree} agree, {len(fixed)} corrected, {filled} filled")
    diag.put("pricecheck", market=name, source=source, date=str(day.date()), checked=len(other),
             agree=agree, corrected=len(fixed), filled=filled)
    for f in fixed[:8]:
        diag.sample("pricecheck", "corrected_eg", f, market=name)
    return close, volume


def psx(close, volume, fund):
    """Use the price on each PSX company page (fund['psx_price'], ['psx_date'])."""
    if "psx_price" not in fund or "psx_date" not in fund:
        return close, volume
    now = datetime.now(ZoneInfo("Asia/Karachi"))
    f = fund[["psx_price", "psx_date", "psx_volume"]].dropna(subset=["psx_price", "psx_date"])
    # during trading hours today's page price is live, not a close
    if now.weekday() < 5 and now.hour * 60 + now.minute < 16 * 60 + 30:
        f = f[f["psx_date"] != now.strftime("%Y-%m-%d")]
    if f.empty:
        return close, volume
    day = f["psx_date"].mode().iloc[0]
    f = f[f["psx_date"] == day]
    return _apply("PSX", close, volume, pd.to_numeric(f["psx_price"]).to_dict(),
                  pd.to_numeric(f["psx_volume"], errors="coerce").to_dict(), day, "PSX exchange")


def _massive_day(day, key):
    url = (f"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{day}"
           f"?adjusted=true&apiKey={key}")
    for i in range(3):
        try:
            r = json.loads(urllib.request.urlopen(url, timeout=60).read())
            return {x["T"].replace(".", "-"): x for x in r.get("results") or []}
        except urllib.error.HTTPError as e:
            if e.code == 429:   # free plan: 5 calls a minute
                time.sleep(15)
                continue
            raise
    return {}


def us(close, volume, index_ticker="SPY"):
    """Returns (close, volume, index_closes {date: close} from Massive, for patching the index)."""
    key = os.environ.get("MASSIVE_API_KEY")
    ix = {}
    if not key:
        diag.put("pricecheck", market="US", source="none (no MASSIVE_API_KEY)")
        return close, volume, ix
    try:
        last = close.index[-1].date()
        now = datetime.now(ZoneInfo("America/New_York"))
        days = [last]
        d = last + timedelta(days=1)
        while d <= now.date() and len(days) < 4:  # later sessions Yahoo may be missing
            if d.weekday() < 5 and (d < now.date() or now.hour * 60 + now.minute >= 16 * 60 + 30):
                days.append(d)
            d += timedelta(days=1)
        for d in days:
            bars = _massive_day(d.isoformat(), key)
            if not bars:
                continue  # holiday or not published yet
            if index_ticker in bars:
                ix[pd.Timestamp(d)] = bars[index_ticker].get("c")
            close, volume = _apply("US", close, volume, {t: b.get("c") for t, b in bars.items()},
                                   {t: b.get("v") for t, b in bars.items()}, d, "Massive")
    except Exception as e:
        print("WARNING price check (Massive) failed:", e)
        diag.sample("pricecheck", "errors", str(e)[:150], market="US")
    return close, volume, ix
