"""One-off check: which free sources give Pakistan (PSX) prices, fundamentals and index lists?"""
import json, urllib.request, io
import pandas as pd, yfinance as yf

out = {}
def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read()

for t in ["OGDC.KA", "HUBC.KA", "LUCK.KA", "^KSE", "^KSE100"]:
    try:
        h = yf.download(t, period="1y", progress=False, auto_adjust=True)
        out[f"yahoo_prices_{t}"] = f"{len(h)} rows, last {h.index[-1].date() if len(h) else None}"
    except Exception as e:
        out[f"yahoo_prices_{t}"] = f"ERR {e}"
for t in ["OGDC.KA", "HUBC.KA"]:
    try:
        i = yf.Ticker(t).info
        out[f"yahoo_info_{t}"] = {k: i.get(k) for k in ["shortName", "sector", "marketCap", "trailingPE", "returnOnEquity", "revenueGrowth"]}
    except Exception as e:
        out[f"yahoo_info_{t}"] = f"ERR {e}"
for name, url in [("psx_eod_OGDC", "https://dps.psx.com.pk/timeseries/eod/OGDC"),
                  ("psx_int_OGDC", "https://dps.psx.com.pk/timeseries/int/OGDC"),
                  ("psx_company_OGDC", "https://dps.psx.com.pk/company/OGDC"),
                  ("psx_indices_KSE100", "https://dps.psx.com.pk/indices/KSE100")]:
    try:
        b = get(url)
        out[name] = f"{len(b)} bytes: " + b[:300].decode(errors="replace")
    except Exception as e:
        out[name] = f"ERR {e}"
try:
    html = get("https://en.wikipedia.org/wiki/KSE_100_Index").decode()
    tabs = pd.read_html(io.StringIO(html))
    out["wiki_kse100_tables"] = [(list(t.columns)[:6], len(t)) for t in tabs][:8]
except Exception as e:
    out["wiki_kse100_tables"] = f"ERR {e}"
try:
    b = get("https://news.google.com/rss/search?q=%22Oil%20%26%20Gas%20Development%20Company%22%20when:10d&hl=en-PK&gl=PK&ceid=PK:en")
    out["gnews_OGDC"] = b.decode(errors="replace").count("<item>")
except Exception as e:
    out["gnews_OGDC"] = f"ERR {e}"
print(json.dumps(out, indent=1, default=str))
open("probe.json", "w").write(json.dumps(out, indent=1, default=str))
