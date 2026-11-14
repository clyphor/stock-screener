"""One place that talks to the AI, so parsing, usage tracking and errors are handled the same way.

Several providers, tried in order — the first that's set up and still working is used:
  1. Claude (ANTHROPIC_API_KEY)          paid, best
  2. Google Gemini (GEMINI_API_KEY)      free tier, needs a free key from aistudio.google.com
  3. GitHub Models (GITHUB_TOKEN)        free, built into GitHub Actions — nothing to sign up for
  4. Groq (GROQ_API_KEY)                 free tier, needs a free key from console.groq.com
If one runs out of credit or hits its daily limit, it's skipped for the rest of the run and the next is used.
If none work, callers fall back to the built-in word list.
"""
import json
import os
import time
import urllib.error
import urllib.request

import diag
from config import CLAUDE_MODEL

PROVIDERS = [
    # name, env var, kind, url, models to try in order
    ("Claude", "ANTHROPIC_API_KEY", "anthropic", "https://api.anthropic.com/v1/messages", [CLAUDE_MODEL]),
    ("Gemini", "GEMINI_API_KEY", "openai", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
     ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]),
    ("GitHub Models", "GITHUB_TOKEN", "openai", "https://models.github.ai/inference/chat/completions",
     ["openai/gpt-4.1-mini", "openai/gpt-4o-mini",
      "https://models.github.ai/inference/v1/chat/completions|openai/gpt-4o-mini"]),
    ("Groq", "GROQ_API_KEY", "openai", "https://api.groq.com/openai/v1/chat/completions",
     ["openai/gpt-oss-120b", "llama-3.3-70b-versatile"]),
]
_dead = {}      # provider -> reason, for this run
_model_ok = {}  # provider -> model that worked
_fails = {}     # consecutive non-fatal failures per provider


def _configured():
    return [p for p in PROVIDERS if os.environ.get(p[1]) and p[0] not in _dead]


def available():
    return bool([p for p in PROVIDERS if os.environ.get(p[1])])


def provider_names():
    return [p[0] for p in PROVIDERS if os.environ.get(p[1])]


def _fatal(code, body):
    """Out of credit, bad key, daily limit: stop using this provider for the rest of the run."""
    b = body.lower()
    return code in (401, 402, 403) or (code == 400 and ("credit" in b or "billing" in b or "api key" in b)) \
        or (code == 429 and any(w in b for w in ("per day", "daily", "quota", "exhausted", "insufficient")))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirected POST silently becomes a GET (and returns a status page) — fail loudly instead."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(f"redirected ({code}) to {newurl}")


_opener = urllib.request.build_opener(_NoRedirect)


def _call(p, model, prompt, max_tokens, timeout):
    name, env, kind, url, _ = p
    if "|" in model:   # "url|model": this model lives at another address
        url, model = model.split("|", 1)
    key = os.environ[env]
    if kind == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    else:
        body = {"model": model, "max_tokens": max_tokens, "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}]}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if name == "GitHub Models":
        headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    headers["User-Agent"] = "stock-screener/1.0 (+https://github.com/clyphor/stock-screener)"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with _opener.open(req, timeout=timeout) as r:
        raw, status, ctype = r.read(), r.status, r.headers.get("Content-Type", "")
        hdr = {k: v for k, v in r.headers.items() if k.lower() in ("server", "x-github-request-id", "x-ms-request-id", "via")}
    try:
        resp = json.loads(raw)
    except ValueError:
        raise RuntimeError(f"non-JSON reply from {url} (HTTP {status}, {ctype}, {len(raw)} bytes, {hdr}): {raw[:200]!r}")
    if kind == "anthropic":
        text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
        u = resp.get("usage", {}) or {}
        usage = (u.get("input_tokens", 0), u.get("output_tokens", 0))
        cut = resp.get("stop_reason") == "max_tokens"
    else:
        ch = (resp.get("choices") or [{}])[0]
        text = (ch.get("message") or {}).get("content") or ""
        u = resp.get("usage", {}) or {}
        usage = (u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        cut = ch.get("finish_reason") == "length"
    return text, usage, cut


def ask(prompt, max_tokens=4000, where="claude", timeout=180):
    """Send one prompt, return the reply text. Tries each working provider in turn. Raises if none work."""
    last = None
    for p in _configured():
        name = p[0]
        models = [_model_ok[name]] if name in _model_ok else p[4]
        for model in models:
            for attempt in range(2):
                try:
                    text, (i, o), cut = _call(p, model, prompt, max_tokens, timeout)
                    if not text:
                        raise RuntimeError("empty reply")
                    _model_ok[name] = model
                    _fails[name] = 0
                    diag.claude_ok({"usage": {"input_tokens": i, "output_tokens": o}}, paid=(name == "Claude"))
                    diag.inc("claude", "by_" + name.lower().replace(" ", "_"))
                    if cut:
                        diag.sample("claude", "errors", f"{where}: reply cut off at max_tokens={max_tokens} ({name})")
                    return text
                except urllib.error.HTTPError as e:
                    body = ""
                    try:
                        body = e.read()[:400].decode(errors="replace")
                    except Exception:
                        pass
                    last = e
                    if e.code == 404 or (e.code == 400 and "model" in body.lower() and "credit" not in body.lower()):
                        break                    # this model name isn't offered — try the next model
                    if _fatal(e.code, body):
                        _dead[name] = f"{e.code}: {body[:120]}"
                        print(f"AI: {name} unavailable for this run ({e.code}) — trying the next provider. {body[:150]}")
                        diag.sample("claude", "errors", f"{where}: {name} stopped — {e.code} {body[:150]}")
                        diag.inc("claude", "failures")
                        break
                    if e.code == 429 and attempt == 0:  # per-minute limit: wait and retry once
                        time.sleep(20)
                        continue
                    diag.sample("claude", "errors", f"{where}: {name} {e.code} {body[:150]}")
                    break
                except Exception as e:  # timeout, connection, bad reply
                    last = e
                    diag.sample("claude", "errors", f"{where}: {name} {str(e)[:150]}")
                    break
            if name in _dead:
                break
            if name in _model_ok and _model_ok[name] == model and last is not None:
                break
        if name not in _dead:
            _fails[name] = _fails.get(name, 0) + 1
            if _fails[name] >= 3:   # keeps failing — stop wasting time on it this run
                _dead[name] = "3 failures in a row"
    diag.inc("claude", "calls")
    diag.inc("claude", "failures")
    raise RuntimeError(f"no AI provider worked ({last})")


def ask_json(prompt, max_tokens=4000, where="claude", kind="array"):
    text = ask(prompt, max_tokens, where)
    o, c = ("[", "]") if kind == "array" else ("{", "}")
    try:
        return json.loads(text[text.index(o): text.rindex(c) + 1])
    except Exception as e:
        diag.inc("claude", "failures")
        diag.sample("claude", "errors", f"{where}: couldn't parse JSON ({e}); reply began: {text[:120]!r}")
        raise
