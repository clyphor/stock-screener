import json, urllib.request, io
import pandas as pd, yfinance as yf
out = {}
for t in ["LUCK.KA", "OGDC.KA", "HBL.KA", "EFERT.KA"]:
    tk = yf.Ticker(t); r = {}
    for name in ("balance_sheet", "income_stmt", "cashflow"):
        try:
            df = getattr(tk, name)
            r[name] = {"cols": [str(c)[:10] for c in df.columns][:4], "rows": len(df),
                       "sample": {k: (None if pd.isna(df.loc[k].iloc[0]) else float(df.loc[k].iloc[0]))
                                  for k in ["Total Debt", "Stockholders Equity", "Common Stock Equity", "Total Assets",
                                            "Net Income", "Total Revenue", "Operating Cash Flow", "Free Cash Flow",
                                            "Cash And Cash Equivalents", "Current Assets", "Current Liabilities"] if k in df.index}}
        except Exception as e:
            r[name] = f"ERR {e}"
    try:
        dv = tk.dividends; r["dividends"] = {"n": len(dv), "last": [(str(i.date()), float(v)) for i, v in dv.tail(3).items()]}
    except Exception as e:
        r["dividends"] = f"ERR {e}"
    out[t] = r
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode(errors="replace")
for s in ["aapl.us", "txn.us", "bhp.au", "cba.au", "^spx"]:
    try:
        txt = get(f"https://stooq.com/q/d/l/?s={s}&i=d")
        out["stooq_" + s] = txt[:60].replace("\n", " | ") + " ... " + txt.strip().splitlines()[-1][:60]
    except Exception as e:
        out["stooq_" + s] = f"ERR {e}"
try:
    txt = get("https://stooq.com/q/l/?s=aapl.us+txn.us+bhp.au&f=sd2t2ohlcv&h&e=csv")
    out["stooq_multi_quote"] = txt[:400]
except Exception as e:
    out["stooq_multi_quote"] = f"ERR {e}"
print(json.dumps(out, indent=1, default=str))
open("probe.json", "w").write(json.dumps(out, indent=1, default=str))
