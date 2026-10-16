"""Shariah (halal) screening.

Pakistan: membership of the official KMI All-Share Islamic Index (PSX), which is screened by
the exchange's Shariah advisors — the authoritative source.

US / ASX: no free official list exists, so we apply the AAOIFI methodology (the standard most
Islamic funds and apps such as Zoya and Musaffa build on):

1. Business activity — core business must be permissible. Excluded: conventional banking,
   lending and insurance, alcohol, tobacco, gambling/casinos, pork, adult entertainment,
   weapons/defence, and cannabis. Some industries are "doubtful" (mixed revenue, e.g. hotels,
   media, REITs, conventional asset managers) and need a closer look.
2. Financial ratios (vs market capitalisation):
   - interest-bearing debt < 30%
   - cash + interest-bearing investments < 30%
   - interest (non-permissible) income < 5% of revenue

Result: HALAL (passes all), DOUBTFUL (permissible business but data missing or a borderline
industry), NOT HALAL (fails a screen). This is an automated approximation, not a fatwa.
"""
import numpy as np
import pandas as pd

PROHIBITED_INDUSTRIES = [
    "banks", "credit services", "mortgage finance", "insurance", "capital markets",
    "beverages - wineries", "beverages - brewers", "distillers", "tobacco", "gambling",
    "resorts & casinos", "aerospace & defense", "reit - mortgage", "financial conglomerates",
    "asset management",
]
DOUBTFUL_INDUSTRIES = [
    "lodging", "entertainment", "broadcasting", "reit -", "real estate services",
    "restaurants", "packaged foods", "farm products", "specialty retail", "discount stores",
    "grocery stores", "pharmaceutical retailers", "department stores", "leisure",
    "financial data & stock exchanges", "insurance brokers",
]
PROHIBITED_NAME_WORDS = ["brewing", "brewery", "winery", "distiller", "casino", "tobacco", "cannabis", "pork"]

DEBT_LIMIT = 0.30
CASH_LIMIT = 0.30
INCOME_LIMIT = 0.05


def screen(ticker, market, sector, industry, name, mcap, total_debt, cash, interest_income, revenue, kmi=None):
    """Returns dict(status, reasons, ratios)."""
    ind = str(industry or "").lower()
    nm = str(name or "").lower()
    reasons = []
    ratios = {}

    if market == "PSX":
        if kmi is None:
            return {"status": "DOUBTFUL", "reasons": ["KMI Islamic index list unavailable today"], "ratios": {}, "method": "KMI"}
        if kmi:
            return {"status": "HALAL", "reasons": ["Member of the KMI All-Share Islamic Index (PSX Shariah-screened)"],
                    "ratios": {}, "method": "KMI"}
        return {"status": "NOT HALAL", "reasons": ["Not in the KMI All-Share Islamic Index"], "ratios": {}, "method": "KMI"}

    # 1) Business activity
    bad = [p for p in PROHIBITED_INDUSTRIES if p in ind] + [w for w in PROHIBITED_NAME_WORDS if w in nm]
    if bad:
        return {"status": "NOT HALAL", "reasons": [f"Business activity not permissible ({industry})"],
                "ratios": {}, "method": "AAOIFI"}
    doubtful_biz = any(p in ind for p in DOUBTFUL_INDUSTRIES)
    if doubtful_biz:
        reasons.append(f"Industry may have mixed revenue ({industry}) — check the company's revenue breakdown")

    # 2) Financial ratios
    def ratio(a, b):
        try:
            a, b = float(a), float(b)
            return a / b if b > 0 and np.isfinite(a) and np.isfinite(b) else None
        except (TypeError, ValueError):
            return None

    d = ratio(total_debt if total_debt is not None else np.nan, mcap)
    c = ratio(cash if cash is not None else np.nan, mcap)
    i = ratio(interest_income if interest_income is not None else np.nan, revenue)
    ratios = {"debt": d, "cash": c, "interest_income": i}
    fails = []
    if d is not None and d >= DEBT_LIMIT:
        fails.append(f"Interest-bearing debt is {d:.0%} of market value (limit 30%)")
    if c is not None and c >= CASH_LIMIT:
        fails.append(f"Cash & interest-bearing investments are {c:.0%} of market value (limit 30%)")
    if i is not None and i >= INCOME_LIMIT:
        fails.append(f"Interest income is {i:.1%} of revenue (limit 5%)")
    if fails:
        return {"status": "NOT HALAL", "reasons": fails + reasons, "ratios": ratios, "method": "AAOIFI"}
    missing = [k for k, v in (("debt", d), ("cash", c)) if v is None]
    if missing:
        reasons.append("Missing data for: " + ", ".join(missing))
    if doubtful_biz or missing:
        return {"status": "DOUBTFUL", "reasons": reasons, "ratios": ratios, "method": "AAOIFI"}
    reasons.insert(0, "Permissible business; debt, cash and interest income within AAOIFI limits")
    return {"status": "HALAL", "reasons": reasons, "ratios": ratios, "method": "AAOIFI"}


def purification(ratios):
    """Share of dividends/gains to give to charity = interest income / revenue (when known)."""
    i = (ratios or {}).get("interest_income")
    return None if i is None else round(float(i), 4)
