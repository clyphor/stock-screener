"""Writes a single mobile-friendly HTML page (served free by GitHub Pages)."""
import json

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Screener</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1c1a;--mute:#6b6a65;--line:#e4e2dc;--acc:#2f6f4f;--neg:#a8432f;--chip:#eef3ef}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--mute:#9a988f;--line:#2e2d2a;--acc:#6fbf93;--neg:#e08a74;--chip:#24302a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,Segoe UI,sans-serif}
header{padding:20px 16px 8px}h1{font-size:22px;margin:0}.sub{color:var(--mute);font-size:13px;margin-top:4px}
.tabs{display:flex;gap:8px;padding:8px 16px;position:sticky;top:0;background:var(--bg);z-index:2}
.tabs button{flex:1;padding:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;font-weight:600;font-size:15px}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.stats{margin:8px 16px;padding:12px;border-radius:12px;background:var(--card);border:1px solid var(--line);font-size:13px;color:var(--mute)}
.stats b{color:var(--ink)}
.card{margin:10px 16px;padding:14px;border-radius:14px;background:var(--card);border:1px solid var(--line)}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.tk{font-weight:700;font-size:17px}.nm{color:var(--mute);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sc{font-size:22px;font-weight:700;color:var(--acc)}.rank{color:var(--mute);font-size:12px;margin-right:6px}
.bars{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:10px 0 6px}
.bar small{display:block;color:var(--mute);font-size:11px}.bar i{display:block;height:6px;border-radius:3px;background:var(--line)}
.bar i span{display:block;height:100%;border-radius:3px;background:var(--acc)}
.meta{font-size:12px;color:var(--mute)}.chips{margin-top:6px}
.chip{display:inline-block;font-size:12px;padding:2px 8px;margin:2px 4px 0 0;border-radius:20px;background:var(--chip)}
.chip.bad{color:var(--neg)}
.sig{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:3px 8px;border-radius:6px;margin-left:8px;vertical-align:3px}
.sig.BUY{background:var(--acc);color:#fff}.sig.WATCH{border:1px solid var(--acc);color:var(--acc)}
.card.BUY{border:2px solid var(--acc)}
.sigbox{margin:8px 16px;padding:12px;border-radius:12px;background:var(--card);border:1px solid var(--line);font-size:14px}
.sigbox h2{font-size:15px;margin:0 0 6px}.sigbox .mute{color:var(--mute);font-size:13px}
footer{padding:16px;color:var(--mute);font-size:12px}
</style></head><body>
<header><h1>Stock Screener</h1><div class="sub" id="gen"></div></header>
<div class="tabs" id="tabs"></div><div id="sigs" class="sigbox"></div><div id="stats" class="stats"></div><div id="list"></div>
<footer>Ranks stocks by a blend of an ML model on price trends, fundamentals vs sector peers, and news sentiment for the company and its competitors. Scores are relative rankings, not price targets. Not financial advice; test on paper first.</footer>
<script>
const D = __DATA__;
const BAD = ["Negative news","Sector headwind","Overbought (RSI)"];
const L = {ml:"Model",fundamental:"Fundamentals",news:"News",peers:"Peers"};
document.getElementById("gen").textContent = "Updated " + D.generated.replace("T"," ").replace("+00:00","") + " UTC" + (D.demo ? " · DEMO DATA" : "");
const tabs = document.getElementById("tabs");
function show(m){
  [...tabs.children].forEach(b=>b.classList.toggle("on", b.textContent===m));
  const s = D.stats[m]||{};
  document.getElementById("stats").innerHTML = s.error ? "Run failed: "+s.error :
    `Backtest since ${s.test_from}: top-20% picks beat bottom-20% by <b>${((s.top_minus_bottom||0)*100).toFixed(2)}%</b> per month on average; ranking accuracy (IC) <b>${s.ic_mean}</b>; top picks beat the index <b>${Math.round((s.top_hit_rate||0)*100)}%</b> of the time. ${s.screened} stocks passed the screen.${s.model_used===false?" <b>Model failed its test here, so it now counts for only 10%.</b>":""} News scored by ${s.news_method}.`;
  const rows = D.markets[m]||[];
  const buys = rows.filter(r=>r.signal==="BUY"), watch = rows.filter(r=>r.signal==="WATCH");
  const tk = r=>r.ticker.replace(".AX","");
  const tr = s.track_n ? `Past signals (${s.track_n} so far): beat the index <b>${Math.round(s.track_win_rate*100)}%</b> of the time, by <b>${(s.track_avg_excess*100).toFixed(2)}%</b> on average.`
                       : `Scorecard starts building from today — check back in a week or two.`;
  document.getElementById("sigs").innerHTML = `<h2>${buys.length ? "Buy signals: "+buys.map(tk).join(", ") : "No buy signals today"}</h2>`
    + (watch.length ? `<div>Watch: ${watch.map(tk).join(", ")}</div>` : "")
    + `<div class="mute" style="margin-top:6px">BUY = top-ranked, in an uptrend, not overbought, solid fundamentals, no bad news${s.model_used ? ", and the price model agrees" : ""}. WATCH = all but one. ${tr}</div>`;
  document.getElementById("list").innerHTML = (D.markets[m]||[]).map((r,i)=>`
   <div class="card ${r.signal||""}"><div class="top"><div style="min-width:0"><span class="rank">#${i+1}</span><span class="tk">${r.ticker.replace(".AX","")}</span>${r.signal?`<span class="sig ${r.signal}">${r.signal}</span>`:""}
   <div class="nm">${r.name||""} · ${r.sector||""}</div></div><div class="sc">${r.score}</div></div>
   <div class="bars">${Object.entries(r.parts).map(([k,v])=>`<div class="bar"><small>${L[k]}</small><i><span style="width:${v}%"></span></i></div>`).join("")}</div>
   <div class="meta">Price ${r.price??"–"} · 3m ${r.ret3m??"–"}% · P/E ${r.pe??"–"}</div>
   <div class="chips">${r.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div></div>`).join("");
}
Object.keys(D.markets).forEach(m=>{const b=document.createElement("button");b.textContent=m;b.onclick=()=>show(m);tabs.appendChild(b)});
show(Object.keys(D.markets)[0]);
</script></body></html>"""


def write_page(payload, path):
    with open(path, "w") as f:
        f.write(PAGE.replace("__DATA__", json.dumps(payload, default=str)))
