import json, datetime as dt
import yfinance as yf
out = {}
today = dt.date.today()
for t in ["SPY", "AAPL", "TXN", "BHP.AX", "OGDC.KA"]:
    a = yf.download(t, period="6y", auto_adjust=True, progress=False)
    b = yf.download(t, start=str(today - dt.timedelta(days=6 * 366)), end=str(today + dt.timedelta(days=2)), auto_adjust=True, progress=False)
    c = yf.Ticker(t).history(period="5d", auto_adjust=True)
    out[t] = {"period_6y_last": str(a.index[-1].date()) if len(a) else None,
              "start_end_last": str(b.index[-1].date()) if len(b) else None,
              "history_5d_last": str(c.index[-1].date()) if len(c) else None,
              "history_5d_tail": [str(x.date()) for x in c.index[-3:]]}
multi = yf.download(["SPY", "AAPL", "TXN"], start=str(today - dt.timedelta(days=6 * 366)), end=str(today + dt.timedelta(days=2)),
                    auto_adjust=True, progress=False, group_by="ticker")
out["multi_start_end_last"] = str(multi.index[-1].date())
out["utc_now"] = dt.datetime.utcnow().isoformat()
print(json.dumps(out, indent=1))
open("probe.json", "w").write(json.dumps(out, indent=1))
