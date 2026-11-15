"""Members-only analysis.

When the SUPABASE_SERVICE_KEY secret is set, the full analysis (signals, tags, prices, every stock page) is
uploaded to the database, where only signed-in users can read it, and the public web page only gets each
stock's ticker, name, sector and score. Without the key everything stays public, as before.
"""
import glob
import json
import os
import urllib.error
import urllib.request

import config
import diag

PUBLIC_FIELDS = ("ticker", "name", "sector", "score", "market", "rank")


def enabled():
    return bool(os.environ.get("SUPABASE_SERVICE_KEY")) and bool(config.SUPABASE_URL)


def _headers():
    key = os.environ["SUPABASE_SERVICE_KEY"]
    h = {"apikey": key, "Content-Type": "application/json",
         "Prefer": "resolution=merge-duplicates,return=minimal"}
    if key.startswith("eyJ"):   # older 'service_role' JWT keys also go in Authorization
        h["Authorization"] = f"Bearer {key}"
    return h


def _upsert(table, rows, conflict, batch=40):
    url = f"{config.SUPABASE_URL}/rest/v1/{table}?on_conflict={conflict}"
    sent = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        req = urllib.request.Request(url, data=json.dumps(chunk, default=str).encode(), headers=_headers(), method="POST")
        try:
            urllib.request.urlopen(req, timeout=60).read()
            sent += len(chunk)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode(errors="replace")
            raise RuntimeError(f"upload to {table} failed ({e.code}): {body}")
    return sent


def publish(payload, run_markets):
    """Upload full rows for the markets just run + every stock page written in docs/stocks. True if it worked."""
    if not enabled():
        return False
    try:
        rows = [{"path": f"rows/{m}.json", "market": m, "body": payload["markets"].get(m, [])} for m in run_markets
                if payload["markets"].get(m) and "parts" in (payload["markets"][m][0] or {})]
        files = []
        for f in glob.glob("docs/stocks/*.json"):
            name = os.path.basename(f)
            try:
                body = json.load(open(f))
            except Exception:
                continue
            files.append({"path": f"stocks/{name}", "market": body.get("market") if isinstance(body, dict) else None,
                          "body": body})
        n = _upsert("analysis_files", rows, "path") + _upsert("analysis_files", files, "path")
        print(f"members-only: uploaded {len(rows)} market lists and {len(files)} stock pages")
        diag.put("members", uploaded=n, market="general")
        return True
    except Exception as e:
        print("WARNING members-only upload failed — publishing the full page publicly this time:", e)
        diag.sample("members", "errors", str(e)[:200], market="general")
        return False


def slim(payload):
    """What visitors without an account get: ticker, name, sector, score (rest is shown blurred)."""
    out = dict(payload, gated=True)
    out["markets"] = {m: [{k: r.get(k) for k in PUBLIC_FIELDS if k in r} for r in rows]
                      for m, rows in payload["markets"].items()}
    return out


def publish_extras(items):
    """items: [{ticker, market, status, msg, row, detail}] — on-demand results, visible only to who asked."""
    if not enabled() or not items:
        return False
    try:
        _upsert("extra_results", items, "ticker", batch=20)
        return True
    except Exception as e:
        print("WARNING could not save on-demand results to the database:", e)
        return False
