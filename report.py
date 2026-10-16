"""Writes the mobile-friendly web page. Per-stock details load from docs/stocks/<TICKER>.json."""
import json

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Screener</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1c1a;--mute:#6b6a65;--line:#e4e2dc;--acc:#2f6f4f;--neg:#b0432c;--chip:#eef3ef;--ma50:#c9822b;--ma200:#5b6fb5;--idx:#9a988f}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--mute:#9a988f;--line:#2e2d2a;--acc:#6fbf93;--neg:#e08a74;--chip:#24302a;--ma50:#e0a75c;--ma200:#8fa0e0;--idx:#77756e}}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,Segoe UI,sans-serif;-webkit-text-size-adjust:100%}
button{font:inherit;color:inherit}
header{padding:20px 16px 8px}h1{font-size:22px;margin:0}.sub{color:var(--mute);font-size:13px;margin-top:4px}
.tabs{display:flex;gap:8px;padding:8px 16px;position:sticky;top:0;background:var(--bg);z-index:2}
.tabs button{flex:1;padding:10px;border:1px solid var(--line);background:var(--card);border-radius:10px;font-weight:600}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.search{margin:4px 16px 0;width:calc(100% - 32px);padding:11px 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);font-size:16px}
.box{margin:10px 16px;padding:12px;border-radius:12px;background:var(--card);border:1px solid var(--line);font-size:14px}
.box h2{font-size:15px;margin:0 0 6px}
.mrow{display:grid;grid-template-columns:1fr 90px 34px;gap:8px;align-items:center;font-size:13px;padding:4px 0}
.mbar{height:7px;border-radius:4px;background:var(--line);position:relative;overflow:hidden}
.mbar span{position:absolute;top:0;bottom:0;border-radius:4px}
.theme{padding:8px 0;border-top:1px solid var(--line)}.theme:first-of-type{border-top:0}
.theme .hl{font-size:12px;color:var(--mute);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mute{color:var(--mute);font-size:13px}
details.box summary{cursor:pointer;color:var(--mute);font-size:13px}
.card{margin:10px 16px;padding:14px;border-radius:14px;background:var(--card);border:1px solid var(--line);cursor:pointer}
.card.BUY{border:2px solid var(--acc)}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.tk{font-weight:700;font-size:17px}.nm{color:var(--mute);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sc{font-size:22px;font-weight:700;color:var(--acc)}.rank{color:var(--mute);font-size:12px;margin-right:6px}
.bars{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin:10px 0 6px}
.bar small{display:block;color:var(--mute);font-size:11px}.bar i{display:block;height:6px;border-radius:3px;background:var(--line)}
.bar i span{display:block;height:100%;border-radius:3px;background:var(--acc)}
.meta{font-size:12px;color:var(--mute)}.chips{margin-top:6px}
.chip{display:inline-block;font-size:12px;padding:2px 8px;margin:2px 4px 0 0;border-radius:20px;background:var(--chip)}
.chip.bad{color:var(--neg)}
.sig{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:3px 8px;border-radius:6px;margin-left:8px;vertical-align:3px}
.sig.BUY{background:var(--acc);color:#fff}.sig.WATCH{border:1px solid var(--acc);color:var(--acc)}
.more{display:block;margin:12px 16px 4px;width:calc(100% - 32px);padding:12px;border-radius:10px;border:1px solid var(--line);background:var(--card);font-weight:600}
footer{padding:16px 16px 40px;color:var(--mute);font-size:12px}
#sheet{position:fixed;inset:0;background:var(--bg);overflow-y:auto;z-index:10;display:none;-webkit-overflow-scrolling:touch}
#sheet.open{display:block}
.shead{position:sticky;top:0;background:var(--bg);display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line);z-index:2}
.back{border:0;background:none;font-size:16px;font-weight:600;color:var(--acc);padding:6px 4px}
.sec{margin:12px 16px;padding:14px;border-radius:14px;background:var(--card);border:1px solid var(--line)}
.sec h3{margin:0 0 10px;font-size:15px}
.hero{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.big{font-size:34px;font-weight:700;color:var(--acc);line-height:1}
.chk{display:flex;gap:10px;align-items:flex-start;padding:5px 0;font-size:14px}
.chk b{width:20px;flex:none;text-align:center}.ok{color:var(--acc)}.no{color:var(--neg)}.skip{color:var(--mute)}
.prow{display:grid;grid-template-columns:1fr 46px;gap:4px 10px;align-items:center;margin:6px 0;font-size:14px}
.prow i{grid-column:1/-1;display:block;height:8px;border-radius:4px;background:var(--line)}
.prow i span{display:block;height:100%;border-radius:4px;background:var(--acc)}
.prow .v{text-align:right;font-weight:600}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.kv{padding:8px 10px;border-radius:10px;background:var(--bg)}.kv small{display:block;color:var(--mute);font-size:12px}.kv b{font-size:15px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:7px 4px;border-bottom:1px solid var(--line);text-align:right}
td:first-child,th:first-child{text-align:left}th{color:var(--mute);font-weight:500;font-size:12px}
.good{color:var(--acc);font-weight:600}.bad{color:var(--neg);font-weight:600}
.news{padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}.news:last-child{border:0}
.news a{color:var(--ink);text-decoration:none}.news .mute{font-size:12px;margin-top:2px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:1px}
.peer{display:flex;justify-content:space-between;gap:8px;padding:9px 0;border-bottom:1px solid var(--line);cursor:pointer;font-size:14px}.peer:last-child{border:0}
.rng{display:flex;gap:6px;margin-bottom:8px}.rng button{flex:1;padding:6px;border-radius:8px;border:1px solid var(--line);background:var(--bg);font-size:13px}
.rng button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.legend{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:var(--mute);margin-top:6px}
.legend span::before{content:"";display:inline-block;width:12px;height:3px;border-radius:2px;margin-right:4px;vertical-align:3px;background:var(--c)}
svg text{fill:var(--mute);font-size:10px}
#tip{font-size:13px;min-height:18px;color:var(--mute)}
</style></head><body>
<header><h1>Stock Screener</h1><div class="sub" id="gen"></div></header>
<div class="tabs" id="tabs"></div>
<input class="search" id="q" placeholder="Search any stock (e.g. CBA, Apple)" autocomplete="off">
<div id="sigs" class="box"></div>
<details class="box" id="macrobox"><summary><b style="color:var(--ink)">Market &amp; politics today</b> <span id="macrosum"></span></summary><div id="macro" style="margin-top:8px"></div></details>
<details class="box" id="statsbox"><summary>How reliable is this? (backtest)</summary><div id="stats" style="margin-top:8px"></div></details>
<div id="list"></div><button class="more" id="more"></button>
<footer>Ranks stocks by blending a price-trend model, fundamentals vs sector peers, and news sentiment for the company and its competitors. Scores are relative rankings, not price targets. Not financial advice — paper-trade first.</footer>
<div id="sheet"></div>
<script>
const D = __DATA__;
const BAD = ["Negative news","Sector headwind","Overbought (RSI)"];
const L = {ml:"Model",fundamental:"Fundam.",news:"News",peers:"Peers",macro:"Macro"};
let M = Object.keys(D.markets)[0], showAll = false;
const $ = id => document.getElementById(id);
const tk = t => t.replace(".AX","");
const pct = (v,d=1) => v==null ? "–" : (v>0?"+":"") + (v*100).toFixed(d) + "%";
const esc = s => String(s??"").replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
$("gen").textContent = "Updated " + D.generated.replace("T"," ").replace("+00:00","") + " UTC" + (D.demo ? " · DEMO DATA" : "");

function card(r, i){
  return `<div class="card ${r.signal||""}" onclick="openStock('${r.ticker}')"><div class="top"><div style="min-width:0"><span class="rank">#${i+1}</span><span class="tk">${tk(r.ticker)}</span>${r.signal?`<span class="sig ${r.signal}">${r.signal}</span>`:""}
   <div class="nm">${esc(r.name)} · ${esc(r.sector)}</div></div><div class="sc">${r.score}</div></div>
   <div class="bars">${Object.entries(r.parts).map(([k,v])=>`<div class="bar"><small>${L[k]}</small><i><span style="width:${v}%"></span></i></div>`).join("")}</div>
   <div class="meta">Price ${r.price??"–"} · 3m ${r.ret3m??"–"}% · P/E ${r.pe??"–"}</div>
   <div class="chips">${r.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div></div>`;
}
function render(){
  [...$("tabs").children].forEach(b=>b.classList.toggle("on", b.textContent===M));
  const s = D.stats[M]||{}, rows = D.markets[M]||[];
  const buys = rows.filter(r=>r.signal==="BUY"), watch = rows.filter(r=>r.signal==="WATCH");
  const link = r => `<a href="#" onclick="openStock('${r.ticker}');return false" style="color:inherit">${tk(r.ticker)}</a>`;
  const tr = s.track_n ? `Past signals (${s.track_n} so far): beat the index <b>${Math.round(s.track_win_rate*100)}%</b> of the time, by <b>${(s.track_avg_excess*100).toFixed(2)}%</b> on average.`
                       : `Scorecard is building — check back in a week or two.`;
  $("sigs").innerHTML = s.error ? `<h2>${M} run failed</h2><div class="mute">${esc(s.error)}</div>` :
    `<h2>${buys.length ? "Buy signals: "+buys.map(link).join(", ") : "No buy signals today"}</h2>`
    + (watch.length ? `<div>Watch: ${watch.map(link).join(", ")}</div>` : "")
    + `<div class="mute" style="margin-top:6px">BUY = passes every check: top-ranked, uptrend, not overbought, solid fundamentals, no bad news, no strong sector/political headwind${s.model_used ? ", price model agrees" : ""}. WATCH = all but one. ${tr}</div>`;
  $("stats").innerHTML = s.error ? "" :
    `Tested on ${s.test_from} onwards (data the model never saw): top-20% picks beat bottom-20% by <b>${((s.top_minus_bottom||0)*100).toFixed(2)}%</b> a month; ranking accuracy (IC) <b>${s.ic_mean}</b> (0 = random); top picks beat the index <b>${Math.round((s.top_hit_rate||0)*100)}%</b> of the time. ${s.screened} stocks passed the screen.<br><br><b>Data check:</b> prices up to ${s.price_date||"–"}; ${Math.round((s.news_coverage||0)*100)}% of stocks had news in the last 10 days (scored by ${s.news_method}).${(s.news_coverage||0)<0.5?" <b>News coverage is low — treat the News and Peers parts with caution.</b>":""}`
    + (s.model_used===false ? " <b>The price model failed this test here, so it counts for only 10%.</b>" : "");
  const mc = s.macro;
  if (mc) {
    const th = Object.values(mc.themes).sort((a,b)=>b.heat-a.heat);
    const sc = Object.entries(mc.sectors).sort((a,b)=>b[1].score-a[1].score);
    const hot = th.filter(t=>t.heat>=0.5).map(t=>t.label);
    $("macrosum").textContent = hot.length ? "· hot: " + hot.join(", ") : "· no unusual political news";
    const bar = v => `<div class="mbar"><span style="left:${v<0?50+v*50:50}%;width:${Math.abs(v)*50}%;background:${v<0?"var(--neg)":"var(--acc)"}"></span></div>`;
    $("macro").innerHTML = `<div class="mute" style="margin-bottom:6px">Political &amp; macro themes — how much each is in the news vs normal:</div>`
      + th.map(t=>`<div class="theme"><div class="mrow" style="grid-template-columns:1fr 90px 34px"><b style="font-weight:600">${esc(t.label)}</b><div class="mbar"><span style="left:0;width:${t.heat*100}%;background:${t.heat>=0.5?"var(--ma50)":"var(--mute)"}"></span></div><span class="mute">${Math.round(t.heat*100)}</span></div>
        ${t.why?`<div class="mute">${esc(t.why)}</div>`:""}${t.headlines.slice(0,2).map(h=>`<div class="hl">• ${h.link?`<a href="${esc(h.link)}" target="_blank" rel="noopener" style="color:inherit">${esc(h.title)}</a>`:esc(h.title)}</div>`).join("")}</div>`).join("")
      + `<div class="mute" style="margin:12px 0 6px">Sector news mood (red = bad for that sector, green = good):</div>`
      + sc.map(([k,v])=>`<div class="mrow"><span>${esc(k)}</span>${bar(v.score)}<span class="mute">${v.score>0?"+":""}${v.score}</span></div>`).join("")
      + `<div class="mute" style="margin-top:8px">Scored by ${mc.method}. Tap a stock to see which themes affect it.</div>`;
  }
  const q = $("q").value.trim().toLowerCase();
  let shown = rows.map((r,i)=>[r,i]);
  if (q) shown = shown.filter(([r])=>r.ticker.toLowerCase().startsWith(q) || (r.name||"").toLowerCase().includes(q));
  else if (!showAll) shown = shown.slice(0, D.top_n);
  $("list").innerHTML = shown.map(([r,i])=>card(r,i)).join("") || `<div class="box mute">No match in ${M}. It may be outside the S&P 500 / ASX 200, or filtered out as too small.</div>`;
  $("more").style.display = q || rows.length <= D.top_n ? "none" : "block";
  $("more").textContent = showAll ? `Show top ${D.top_n} only` : `Show all ${rows.length} ranked stocks`;
}
$("more").onclick = ()=>{ showAll=!showAll; render(); };
$("q").oninput = render;
Object.keys(D.markets).forEach(m=>{const b=document.createElement("button");b.textContent=m;b.onclick=()=>{M=m;showAll=false;$("q").value="";render()};$("tabs").appendChild(b)});
render();

const cache = {};
async function getJSON(u){ if(!cache[u]){ const r = await fetch(u); if(!r.ok) throw new Error(r.status); cache[u] = await r.json(); } return cache[u]; }
function fmtCap(v){ if(v==null) return "–"; const a=Math.abs(v); return a>=1e12?(v/1e12).toFixed(2)+"T":a>=1e9?(v/1e9).toFixed(1)+"B":(v/1e6).toFixed(0)+"M"; }
function fmtF(v, kind){
  if (v==null) return "–";
  if (kind==="pct") return (v*100).toFixed(1)+"%";
  if (kind==="x100") return (v/100).toFixed(2)+"x";
  if (kind==="dy") return (v<0.2? v*100 : v).toFixed(2)+"%";
  return v.toFixed(1)+"x";
}
function sentColor(s){ return s>0.15?"var(--acc)":s<-0.15?"var(--neg)":"var(--mute)"; }

async function openStock(t, push=true){
  const sh = $("sheet");
  sh.innerHTML = `<div class="shead"><button class="back" onclick="history.back()">‹ Back</button><b>${tk(t)}</b></div><div class="sec mute">Loading…</div>`;
  sh.classList.add("open"); sh.scrollTop = 0; document.body.style.overflow="hidden";
  if (push) history.pushState({t}, "", "#"+t);
  let d, base;
  try { d = await getJSON(`stocks/${t}.json`); base = await getJSON(`stocks/_${d.market}.json`); }
  catch(e){ sh.innerHTML = sh.innerHTML.replace("Loading…","Details not available for this stock yet."); return; }
  const up = d.analyst.target && d.price ? d.analyst.target/d.price-1 : null;
  sh.innerHTML = `<div class="shead"><button class="back" onclick="history.back()">‹ Back</button><b>${tk(d.ticker)}</b>${d.signal?`<span class="sig ${d.signal}">${d.signal}</span>`:""}</div>
  <div class="sec"><div class="hero"><div style="min-width:0"><div class="tk" style="font-size:20px">${esc(d.name)}</div>
    <div class="mute">${esc(d.sector)}${d.industry?" · "+esc(d.industry):""}</div>
    <div style="margin-top:8px">Price <b>${d.price??"–"}</b> · Market cap <b>${fmtCap(d.mcap)}</b></div></div>
    <div style="text-align:right"><div class="big">${d.score}</div><div class="mute">#${d.rank} of ${d.of}</div></div></div>
    <div class="chips" style="margin-top:8px">${d.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div></div>

  <div class="sec"><h3>${d.signal==="BUY"?"Buy signal — every check passed":d.signal==="WATCH"?"Watch — one check short of a buy":"Buy-signal checklist"}</h3>
    ${d.checks.map(c=>`<div class="chk"><b class="${c.skipped?"skip":c.pass?"ok":"no"}">${c.skipped?"–":c.pass?"✓":"✗"}</b><span>${c.label}${c.skipped?' <span class="mute">(not used: model failed its test in this market)</span>':""}</span></div>`).join("")}</div>

  <div class="sec"><h3>Score breakdown</h3><div class="mute" style="margin-bottom:6px">Each part is a 0–100 rank vs the other ${d.market} stocks, weighted into the total.</div>
    ${d.parts.map(p=>`<div class="prow"><span>${p.label} <span class="mute">× ${Math.round(p.weight*100)}%</span></span><span class="v">${p.value}</span><i><span style="width:${p.value}%"></span></i></div>`).join("")}
    <div class="grid" style="margin-top:10px"><div class="kv"><small>Value vs sector</small><b>${d.sub.value}</b></div><div class="kv"><small>Quality</small><b>${d.sub.quality}</b></div><div class="kv"><small>Growth</small><b>${d.sub.growth}</b></div><div class="kv"><small>Analysts</small><b>${d.analyst.rating?esc(d.analyst.rating).replace("_"," "):"–"}</b></div></div>
    ${up!=null?`<div class="mute" style="margin-top:8px">Average analyst target ${d.analyst.target} (${pct(up)} from here).</div>`:""}</div>

  <div class="sec"><h3>Price chart</h3><div class="rng" id="rng"></div><div id="chart"></div><div id="tip"></div>
    <div class="legend"><span style="--c:var(--acc)">Price</span><span style="--c:var(--ma50)">50-day avg</span><span style="--c:var(--ma200)">200-day avg</span><span style="--c:var(--idx)">Index (scaled)</span></div></div>

  <div class="sec"><h3>Technicals</h3><div class="grid">${Object.entries(d.tech).map(([k,v])=>{
      const isPct = !/RSI|Volume/.test(k), s = v==null?"–": /Volatility/.test(k)? (v*100).toFixed(1)+"%" : isPct? pct(v) : (k.startsWith("Volume")? v.toFixed(2)+"x" : v);
      const cls = v==null?"": k.startsWith("RSI") ? (v>70?"bad":v<30?"good":"") : isPct && !/Volatility/.test(k) ? (v>0?"good":"bad") : "";
      return `<div class="kv"><small>${k}</small><b class="${cls}">${s}</b></div>`}).join("")}</div></div>

  <div class="sec"><h3>Fundamentals vs sector</h3><table><tr><th>Metric</th><th>${tk(d.ticker)}</th><th>Sector median</th></tr>
    ${d.fund.map(f=>{ let cls=""; if(f.value!=null&&f.sector!=null){ const better = f.better==="high" ? f.value>f.sector : f.value<f.sector; cls = better?"good":"bad"; }
      return `<tr><td>${f.label}</td><td class="${cls}">${fmtF(f.value,f.kind)}</td><td>${fmtF(f.sector,f.kind)}</td></tr>`}).join("")}</table>
    <div class="mute" style="margin-top:6px">Green = better than the typical company in its sector.</div></div>

  <div class="sec"><h3>News (last 10 days)</h3>
    <div class="mute" style="margin-bottom:6px">Average sentiment: <b style="color:${sentColor(d.news_avg)}">${d.news_avg??0}</b> · competitors: <b style="color:${sentColor(d.peer_avg)}">${d.peer_avg??0}</b>${d.macro_share>0?` · ${Math.round(d.macro_share*100)}% about policy/macro`:""}</div>
    ${d.news.length ? d.news.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}
      <div class="mute">${esc(n.publisher||"")} ${n.date||""}${n.macro?" · policy/macro":""}</div></div>`).join("") : `<div class="mute">No recent headlines.</div>`}</div>

  <div class="sec"><h3>Sector &amp; politics</h3>
    <div class="grid"><div class="kv"><small>Macro score (−1 to 1)</small><b class="${d.macro.score>0.05?"good":d.macro.score<-0.05?"bad":""}">${d.macro.score>0?"+":""}${d.macro.score}</b></div>
    <div class="kv"><small>${esc(d.sector)} news mood</small><b class="${d.macro.sector_news>0.05?"good":d.macro.sector_news<-0.05?"bad":""}">${d.macro.sector_news>0?"+":""}${d.macro.sector_news}</b></div></div>
    ${d.macro.sector_why?`<div class="mute" style="margin-top:8px">${esc(d.macro.sector_why)}</div>`:""}
    ${d.macro.effects.length?`<div style="margin-top:10px;font-size:14px">${d.macro.effects.map(e=>`<div class="chk"><b class="${e.effect>0?"ok":"no"}">${e.effect>0?"▲":"▼"}</b><span>${esc(e.theme)} <span class="mute">(${e.effect>0?"+":""}${e.effect})</span></span></div>`).join("")}</div>`:`<div class="mute" style="margin-top:8px">No political or macro theme is notably affecting this stock right now.</div>`}
    ${d.macro.sector_headlines.length?`<div class="mute" style="margin:8px 0 2px">Sector headlines:</div>`+d.macro.sector_headlines.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}<div class="mute">${esc(n.publisher||"")} ${n.date||""}</div></div>`).join(""):""}</div>

  <div class="sec"><h3>Peers in ${esc(d.sector)}</h3>
    ${d.peers.length ? d.peers.map(p=>`<div class="peer" onclick="openStock('${p.ticker}')"><span><b>${tk(p.ticker)}</b>${p.signal?`<span class="sig ${p.signal}">${p.signal}</span>`:""}<div class="mute">${esc(p.name)}</div></span>
      <span style="text-align:right"><b>${p.score}</b><div class="mute">3m ${pct(p.ret3m,0)} · P/E ${p.pe??"–"} · news <span style="color:${sentColor(p.news)}">${p.news??0}</span></div></span></div>`).join("") : `<div class="mute">No peers in the screened list.</div>`}</div>
  <footer>Not financial advice. Data from Yahoo Finance; may be delayed or incomplete.</footer>`;
  drawChart(d, base, 252);
}

function sma(a, n){ const o=[]; let s=0, c=0; for(let i=0;i<a.length;i++){ const v=a[i]; if(v!=null){s+=v;c++;} if(i>=n){ const w=a[i-n]; if(w!=null){s-=w;c--;} } o.push(i>=n-1 && c===n ? s/n : null); } return o; }
function drawChart(d, base, span){
  $("rng").innerHTML = [[63,"3M"],[126,"6M"],[252,"1Y"]].map(([n,l])=>`<button class="${n===span?"on":""}" onclick='drawChart(cache["stocks/${d.ticker}.json"], cache["stocks/_${d.market}.json"], ${n})'>${l}</button>`).join("");
  const c = d.close, m50 = sma(c,50), m200 = sma(c,200), N = c.length, s0 = Math.max(0, N-span);
  const dates = base.dates.slice(s0), P = c.slice(s0), A = m50.slice(s0), B = m200.slice(s0);
  const ix = base.index.slice(s0), i0 = ix.find(v=>v!=null), p0 = P.find(v=>v!=null);
  const I = ix.map(v=> v==null||i0==null||p0==null ? null : v/i0*p0);
  const all = [...P,...A,...B,...I].filter(v=>v!=null);
  if (!all.length){ $("chart").innerHTML='<div class="mute">No price history.</div>'; return; }
  const lo = Math.min(...all), hi = Math.max(...all), W = 340, H = 190, pl = 4, pr = 40, pt = 8, pb = 18;
  const X = i => pl + i*(W-pl-pr)/Math.max(1,P.length-1), Y = v => pt + (hi-v)/(hi-lo||1)*(H-pt-pb);
  const path = arr => { let s="", pen=false; arr.forEach((v,i)=>{ if(v==null){pen=false;return;} s += (pen?"L":"M")+X(i).toFixed(1)+" "+Y(v).toFixed(1); pen=true; }); return s; };
  const ticks = [lo, (lo+hi)/2, hi].map(v=>`<text x="${W-pr+4}" y="${Y(v)+3}">${v.toFixed(v<10?2:0)}</text><line x1="${pl}" x2="${W-pr}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/>`).join("");
  const mlab = [0, Math.floor(P.length/2), P.length-1].map(i=>`<text x="${Math.min(X(i), W-pr-50)}" y="${H-4}">${dates[i]||""}</text>`).join("");
  $("chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" style="touch-action:pan-y">${ticks}${mlab}
    <path d="${path(I)}" fill="none" stroke="var(--idx)" stroke-width="1" stroke-dasharray="3 3"/>
    <path d="${path(B)}" fill="none" stroke="var(--ma200)" stroke-width="1.4"/>
    <path d="${path(A)}" fill="none" stroke="var(--ma50)" stroke-width="1.4"/>
    <path d="${path(P)}" fill="none" stroke="var(--acc)" stroke-width="2"/>
    <line id="cx" y1="${pt}" y2="${H-pb}" stroke="var(--mute)" stroke-width="0.6" visibility="hidden"/></svg>`;
  const svg = $("chart").querySelector("svg"), cx = svg.querySelector("#cx");
  const move = e => { const r = svg.getBoundingClientRect(); const x = (e.clientX - r.left) * W / r.width;
    const i = Math.max(0, Math.min(P.length-1, Math.round((x-pl)/((W-pl-pr)/Math.max(1,P.length-1)))));
    cx.setAttribute("x1", X(i)); cx.setAttribute("x2", X(i)); cx.setAttribute("visibility","visible");
    $("tip").textContent = `${dates[i]}: ${P[i]?.toFixed(2) ?? "–"}` + (A[i]?` · 50d ${A[i].toFixed(2)}`:"") + (B[i]?` · 200d ${B[i].toFixed(2)}`:""); };
  svg.addEventListener("pointermove", move); svg.addEventListener("pointerdown", move);
  const chg = p0 && P[P.length-1] ? P[P.length-1]/p0-1 : null;
  $("tip").textContent = chg!=null ? `Change over period: ${pct(chg)} · tap the chart for prices` : "";
}
function closeSheet(){ $("sheet").classList.remove("open"); document.body.style.overflow=""; }
window.addEventListener("popstate", e => { if (e.state && e.state.t) openStock(e.state.t, false); else closeSheet(); });
if (location.hash.length > 1) { history.replaceState(null, "", location.pathname); openStock(decodeURIComponent(location.hash.slice(1))); }
</script></body></html>"""


def write_page(payload, path):
    with open(path, "w") as f:
        f.write(PAGE.replace("__DATA__", json.dumps(payload, default=str, separators=(",", ":"))))
