"""Runs every 15 minutes (stdlib only, ~2 seconds):
1) Which requested stocks still need analysing?  -> prints tickers=A,B for the on-demand job.
2) Watchdog: did today's scheduled daily run happen? If not, prints run_daily=1 so the job starts it.
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")
import config  # noqa: E402

SITE = "https://clyphor.github.io/stock-screener/"


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "screener"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def main():
    now = datetime.now(timezone.utc)
    try:
        req = get(config.SUPABASE_URL + "/rest/v1/rpc/requested_tickers", b"{}",
                  {"apikey": config.SUPABASE_ANON_KEY, "Content-Type": "application/json"})
    except Exception as e:
        print(f"# could not read requests: {e}", file=sys.stderr)
        req = []
    site_ok = True
    try:
        data = get(SITE + "data.json?t=" + str(now.timestamp()))
    except Exception as e:
        print(f"# could not read the live page data: {e}", file=sys.stderr)
        data, site_ok = {"markets": {}, "generated": "1970-01-01T00:00+00:00"}, False
    try:
        ex = get(SITE + "extras.json?t=" + str(now.timestamp()))
    except Exception:
        ex = {"items": {}}
    done = {r["ticker"] for rows in data.get("markets", {}).values() for r in rows}
    for t, it in ex.get("items", {}).items():
        when = it.get("when") or ex.get("generated") or ""
        recent = when and datetime.fromisoformat(when) > now - timedelta(hours=6)
        if it.get("status") in ("ok", "not_found") or (it.get("status") == "waiting" and recent):
            done.add(t)
    todo = [r["ticker"] for r in req if r["ticker"] not in done]
    print("tickers=" + ",".join(todo[:25]))

    # Watchdog: for each market, the latest scheduled slot that is at least 40 minutes old —
    # if the page's update time for that market is older, the scheduled run was skipped.
    late = []
    upd = data.get("updated") or {}
    for m, (_, hh, mm, days) in config.SCHEDULE.items():
        slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        while slot > now - timedelta(minutes=40) or slot.weekday() not in days:
            slot -= timedelta(days=1)
        last = datetime.fromisoformat(upd.get(m) or data.get("generated", "1970-01-01T00:00+00:00"))
        if last < slot:
            late.append(m)
        print(f"# {m}: last update {last.isoformat()} due slot {slot.isoformat()}", file=sys.stderr)
    print("run_daily=" + (",".join(late) if site_ok else ""))   # never fire blind
    print(f"# requests={len(req)} pending={len(todo)}", file=sys.stderr)


if __name__ == "__main__":
    main()
