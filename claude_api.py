"""One place that talks to the Claude API, so parsing, usage tracking and errors are handled the same way."""
import json
import os
import urllib.request

import diag
from config import CLAUDE_MODEL


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def ask(prompt, max_tokens=4000, where="claude", timeout=180):
    """Send one prompt, return the reply text (all text blocks joined). Raises on failure (after logging)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no API key")
    body = json.dumps({"model": CLAUDE_MODEL, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
    except Exception as e:
        diag.claude_fail(e, where)
        raise
    diag.claude_ok(resp)
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    if not text:
        err = RuntimeError(f"no text in reply (stop_reason={resp.get('stop_reason')}, "
                           f"blocks={[b.get('type') for b in resp.get('content', [])]})")
        diag.sample("claude", "errors", f"{where}: {err}")
        diag.inc("claude", "failures")
        raise err
    if resp.get("stop_reason") == "max_tokens":
        diag.sample("claude", "errors", f"{where}: reply cut off at max_tokens={max_tokens}")
    return text


def ask_json(prompt, max_tokens=4000, where="claude", kind="array"):
    text = ask(prompt, max_tokens, where)
    o, c = ("[", "]") if kind == "array" else ("{", "}")
    try:
        return json.loads(text[text.index(o): text.rindex(c) + 1])
    except Exception as e:
        diag.inc("claude", "failures")
        diag.sample("claude", "errors", f"{where}: couldn't parse JSON ({e}); reply began: {text[:120]!r}")
        raise
