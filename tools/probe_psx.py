"""Second check: Yahoo coverage of KSE-100, PSX data-portal price history and fundamentals."""
import json, re, urllib.request, urllib.parse, io
import pandas as pd, yfinance as yf

out = {}
def get(url, data=None, ref=None):
    h = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(req, timeout=30).read()

# KSE-100 list from PSX
html = get("https://dps.psx.com.pk/indices/KSE100").decode()
syms = re.findall(r'<td[^>]*><a[^>]*href="/company/([A-Z0-9]+)"', html) or re.findall(r'/company/([A-Z0-9]+)"', html)
syms = list(dict.fromkeys(syms))
out["kse100_symbols"] = [len(syms), syms[:10]]
out["kse100_row_sample"] = re.sub(r"\s+", " ", html[html.find("<tbody"):html.find("<tbody") + 900])

# Yahoo coverage
raw = yf.download([s + ".KA" for s in syms], period="2y", progress=False, auto_adjust=True, group_by="ticker", threads=True)
ok = [s for s in syms if (s + ".KA") in raw.columns.get_level_values(0) and raw[s + ".KA"]["Close"].notna().sum() > 260]
out["yahoo_coverage"] = [len(ok), len(syms), [s for s in syms if s not in ok][:30]]

# PSX company page: find data endpoints and fundamentals text
page = get("https://dps.psx.com.pk/company/HUBC").decode()
out["company_endpoints"] = sorted(set(re.findall(r'["\'](/(?:timeseries|historical|company|financial|data)[^"\']{0,60})["\']', page)))[:40]
txt = re.sub(r"<[^>]+>", " ", page); txt = re.sub(r"\s+", " ", txt)
for kw in ["P/E", "EPS", "Market Cap", "Dividend", "Book Value", "Profit", "Sales", "Shares"]:
    i = txt.find(kw); out["company_text_" + kw] = txt[max(0, i - 60): i + 160] if i >= 0 else None
scripts = re.findall(r"<script[^>]*src=\"([^\"]+)\"", page)
out["scripts"] = scripts[:10]

for name, url, data in [
    ("hist_post", "https://dps.psx.com.pk/historical", urllib.parse.urlencode({"month": "9", "year": "2026", "symbol": "HUBC"}).encode()),
    ("ts_eod_HUBC", "https://dps.psx.com.pk/timeseries/eod/HUBC", None),
    ("ts_int_HUBC", "https://dps.psx.com.pk/timeseries/int/HUBC", None),
    ("ts_KSE100", "https://dps.psx.com.pk/timeseries/eod/KSE100", None),
]:
    try:
        b = get(url, data, ref="https://dps.psx.com.pk/")
        out[name] = f"{len(b)} bytes: " + b[:400].decode(errors="replace")
    except Exception as e:
        out[name] = f"ERR {e}"
open("probe.json", "w").write(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str)[:3000])
