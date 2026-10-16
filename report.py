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
.clock{margin:6px 16px 0;padding:10px 12px;border-radius:12px;background:var(--card);border:1px solid var(--line);font-size:14px;display:flex;justify-content:space-between;gap:8px;align-items:center}
.clock .st{font-weight:700;white-space:nowrap}.clock .open{color:var(--acc)}.clock .closed{color:var(--neg)}
.fbar{display:flex;gap:8px;margin:10px 16px 0}
.fbar button{padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);font-weight:600;font-size:14px}
.fbar button.on{border-color:var(--acc);color:var(--acc)}
#fpanel{display:none;margin:10px 16px;padding:14px;border-radius:14px;background:var(--card);border:1px solid var(--line)}
#fpanel.open{display:block}
.fg{margin-bottom:14px}.fg>label,.fg>.fl{display:block;font-size:13px;font-weight:600;margin-bottom:6px}
.pills{display:flex;flex-wrap:wrap;gap:6px}
.pill{padding:6px 10px;border-radius:20px;border:1px solid var(--line);background:var(--bg);font-size:13px}
.pill.on{background:var(--acc);border-color:var(--acc);color:#fff}
.pill.neg.on{background:var(--neg);border-color:var(--neg)}
.rangerow{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center}
.rangerow input,.fg select{width:100%;padding:9px 10px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:16px}
.sl{display:grid;grid-template-columns:110px 1fr 34px;gap:8px;align-items:center;font-size:13px;margin:4px 0}
.sl input{width:100%;accent-color:var(--acc)}
.fact{display:flex;gap:8px;position:sticky;bottom:0;background:var(--card);padding-top:8px}
.fact button{flex:1;padding:11px;border-radius:10px;border:1px solid var(--line);background:var(--bg);font-weight:600}
.fact button.pri{background:var(--acc);color:#fff;border-color:var(--acc)}
.count{margin:8px 16px 0;font-size:13px;color:var(--mute)}
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
<div class="clock" id="clock"></div>
<input class="search" id="q" placeholder="Search any stock (e.g. CBA, Apple, OGDC)" autocomplete="off">
<div id="sigs" class="box"></div>
<details class="box" id="macrobox"><summary><b style="color:var(--ink)">Market &amp; politics today</b> <span id="macrosum"></span></summary><div id="macro" style="margin-top:8px"></div></details>
<details class="box" id="statsbox"><summary>How reliable is this? (backtest)</summary><div id="stats" style="margin-top:8px"></div></details>
<div class="fbar"><button id="fbtn">Filters</button><button id="sortbtn" style="flex:1;text-align:left"></button><button id="freset" style="display:none">Clear</button></div>
<div id="fpanel"></div>
<div class="count" id="count"></div>
<div id="list"></div><button class="more" id="more"></button>
<footer>Ranks stocks by blending a price-trend model, fundamentals vs sector peers, and news sentiment for the company and its competitors. Scores are relative rankings, not price targets. Not financial advice — paper-trade first.</footer>
<div id="sheet"></div>
<script>
const D = __DATA__;
const BAD = ["Negative news","Sector headwind","Overbought (RSI)","Macro headwind",__BAD_EVENTS__];
const L = {ml:"Model",fundamental:"Fundam.",news:"News",peers:"Peers",macro:"Macro"};
let M = Object.keys(D.markets)[0], showAll = false;
const $ = id => document.getElementById(id);
const tk = t => t.replace(".AX","").replace(".KA","");
const pct = (v,d=1) => v==null ? "–" : (v>0?"+":"") + (v*100).toFixed(d) + "%";
const esc = s => String(s??"").replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
$("gen").textContent = "Updated " + new Date(D.generated).toLocaleString(undefined,{weekday:"short",day:"numeric",month:"short",hour:"numeric",minute:"2-digit",timeZoneName:"short"}) + (D.demo ? " · DEMO DATA" : "");

function card(r, i){
  return `<div class="card ${r.signal||""}" onclick="openStock('${r.ticker}')"><div class="top"><div style="min-width:0"><span class="rank">#${i+1}</span><span class="tk">${tk(r.ticker)}</span>${r.signal?`<span class="sig ${r.signal}">${r.signal}</span>`:""}
   <div class="nm">${esc(r.name)} · ${esc(r.sector)}</div></div><div class="sc">${r.score}</div></div>
   <div class="bars">${Object.entries(r.parts).map(([k,v])=>`<div class="bar"><small>${L[k]}</small><i><span style="width:${v}%"></span></i></div>`).join("")}</div>
   <div class="meta">Price ${r.price??"–"}${M==="PSX"?" PKR":""} · 3m ${r.ret3m??"–"}% · P/E ${r.pe??"–"}</div>
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
    `Tested on ${s.test_from} onwards (data the model never saw): top-20% picks beat bottom-20% by <b>${((s.top_minus_bottom||0)*100).toFixed(2)}%</b> a month; ranking accuracy (IC) <b>${s.ic_mean}</b> (0 = random); top picks beat the index <b>${Math.round((s.top_hit_rate||0)*100)}%</b> of the time. ${s.screened} stocks passed the screen.<br><br><b>Data check:</b> prices up to the ${s.price_date||"–"} close (holidays not shown on the clock); ${Math.round((s.news_coverage||0)*100)}% of stocks had news in the last 10 days (scored by ${s.news_method}). AI scoring: <b>${s.ai_scoring==="on"||s.ai_scoring===true?"on":s.ai_scoring==="failed"?"FAILED today (out of API credit or key problem) — using free rules":"off — add an ANTHROPIC_API_KEY secret to turn it on"}</b>.${(s.news_coverage||0)<0.5?" <b>News coverage is low — treat the News and Peers parts with caution.</b>":""}`
    + (s.model_used===false ? " <b>The price model failed this test here, so it counts for only 10%.</b>" : "");
  const mc = s.macro;
  if (mc) {
    const th = Object.values(mc.themes).sort((a,b)=>b.heat-a.heat);
    const sc = Object.entries(mc.sectors).sort((a,b)=>b[1].score-a[1].score);
    const hot = th.filter(t=>t.heat>=0.5).map(t=>t.label);
    $("macrosum").textContent = (s.ai_scoring==="failed" ? "· ⚠ AI off today (check API credit) " : "") + (hot.length ? "· hot: " + hot.join(", ") : "· no unusual political news");
    const bar = v => `<div class="mbar"><span style="left:${v<0?50+v*50:50}%;width:${Math.abs(v)*50}%;background:${v<0?"var(--neg)":"var(--acc)"}"></span></div>`;
    const evs = mc.events || [];
    $("macro").innerHTML = (evs.length ? `<div class="mute" style="margin-bottom:6px"><b style="color:var(--ink)">Key events today</b> (AI analyst — including second-order effects):</div>`
        + evs.map(e=>`<div class="theme"><b style="font-weight:600">${esc(e.event)}</b><div class="mute">${esc(e.why)}</div>
          <div class="chips">${e.impacts.slice(0,6).map(i=>`<span class="chip ${i.effect<0?"bad":""}">${i.effect>0?"▲":"▼"} ${esc(String(i.target).split(":").slice(1).join(":").replace(".AX",""))}</span>`).join("")}</div></div>`).join("")
        + `<div style="height:12px"></div>`
      : `<div class="mute" style="margin-bottom:8px">Tip: add an Anthropic API key to turn on the AI event analyst, which spots specific events (e.g. a minerals deal or a change in who controls an oil supply) and works out which stocks they affect.</div>`)
      + `<div class="mute" style="margin-bottom:6px">Themes — how much each is in the news vs normal (top 12):</div>`
      + th.slice(0,12).map(t=>`<div class="theme"><div class="mrow" style="grid-template-columns:1fr 90px 34px"><b style="font-weight:600">${esc(t.label)}</b><div class="mbar"><span style="left:0;width:${t.heat*100}%;background:${t.heat>=0.5?"var(--ma50)":"var(--mute)"}"></span></div><span class="mute">${Math.round(t.heat*100)}</span></div>
        ${t.why?`<div class="mute">${esc(t.why)}</div>`:""}${t.headlines.slice(0,2).map(h=>`<div class="hl">• ${h.link?`<a href="${esc(h.link)}" target="_blank" rel="noopener" style="color:inherit">${esc(h.title)}</a>`:esc(h.title)}</div>`).join("")}</div>`).join("")
      + `<div class="mute" style="margin:12px 0 6px">Sector news mood (red = bad for that sector, green = good):</div>`
      + sc.map(([k,v])=>`<div class="mrow"><span>${esc(k)}</span>${bar(v.score)}<span class="mute">${v.score>0?"+":""}${v.score}</span></div>`).join("")
      + `<div class="mute" style="margin-top:8px">Scored by ${mc.method}. Tap a stock to see which themes affect it.</div>`;
  }
  const q = $("q").value.trim().toLowerCase();
  const F = getF();
  let shown = rows.map((r,i)=>[r,i]);
  if (q) shown = shown.filter(([r])=>r.ticker.toLowerCase().startsWith(q) || (r.name||"").toLowerCase().includes(q));
  const active = activeCount(F);
  shown = shown.filter(([r])=>passes(r,F));
  const key = SORTS[F.sort] ? F.sort : "score";
  if (key !== "score") shown.sort((a,b)=>SORTS[key].f(a[0],b[0]));
  const total = shown.length;
  if (!q && !active && !showAll) shown = shown.slice(0, D.top_n);
  $("count").textContent = (q||active) ? `${total} of ${rows.length} ${M} stocks match` : "";
  $("list").innerHTML = shown.map(([r,i])=>card(r,i)).join("") || `<div class="box mute">No stocks match. ${active?"Try loosening the filters.":"It may be outside the S&P 500 / ASX 200 / KSE-100, or filtered out as too small."}</div>`;
  $("more").style.display = q || active || rows.length <= D.top_n ? "none" : "block";
  $("more").textContent = showAll ? `Show top ${D.top_n} only` : `Show all ${rows.length} ranked stocks`;
  $("fbtn").textContent = active ? `Filters (${active})` : "Filters";
  $("fbtn").classList.toggle("on", !!active);
  $("freset").style.display = active ? "block" : "none";
  $("sortbtn").textContent = "Sort: " + SORTS[key].l;
  if ($("fpanel").classList.contains("open")) drawPanel();
  clockTick();
}

/* ---------------- filters ---------------- */
const PARTS = [["ml","Price model"],["fundamental","Fundamentals"],["news","Company news"],["peers","Competitors' news"],["macro","Sector & politics"]];
const SORTS = {
  score:{l:"Score (high→low)", f:(a,b)=>b.score-a.score},
  ml:{l:"Price model", f:(a,b)=>b.parts.ml-a.parts.ml},
  fundamental:{l:"Fundamentals", f:(a,b)=>b.parts.fundamental-a.parts.fundamental},
  news:{l:"Company news", f:(a,b)=>(b.ns??-9)-(a.ns??-9)},
  macro:{l:"Sector & politics", f:(a,b)=>(b.ms??-9)-(a.ms??-9)},
  ret_hi:{l:"3-month return (high→low)", f:(a,b)=>(b.ret3m??-1e9)-(a.ret3m??-1e9)},
  ret_lo:{l:"3-month return (low→high)", f:(a,b)=>(a.ret3m??1e9)-(b.ret3m??1e9)},
  pe_lo:{l:"P/E (cheapest first)", f:(a,b)=>((a.pe>0?a.pe:1e9)-(b.pe>0?b.pe:1e9))},
  rsi_lo:{l:"RSI (most oversold first)", f:(a,b)=>(a.rsi??999)-(b.rsi??999)},
  mcap:{l:"Market cap (largest first)", f:(a,b)=>(b.mcap??0)-(a.mcap??0)},
};
const DEF = () => ({sig:[], sec:[], smin:"", smax:"", parts:{}, pemin:"", pemax:"", rmin:"", rmax:"", rsimin:"", rsimax:"",
  cap:"", news:"", macro:"", good:[], bad:[], tags:[], sort:"score", vqmin:{}});
const FS = {};
function getF(){ if(!FS[M]){ try{ FS[M] = Object.assign(DEF(), JSON.parse(localStorage.getItem("f_"+M)||"{}")); }catch(e){ FS[M]=DEF(); } } return FS[M]; }
function saveF(){ try{ localStorage.setItem("f_"+M, JSON.stringify(FS[M])); }catch(e){} }
const num = v => v===""||v==null ? null : Number(v);
function activeCount(F){ let n=0;
  if(F.sig.length) n++; if(F.sec.length) n++; if(F.smin!==""||F.smax!=="") n++;
  n += Object.values(F.parts).filter(v=>v>0).length; n += Object.values(F.vqmin).filter(v=>v>0).length;
  if(F.pemin!==""||F.pemax!=="") n++; if(F.rmin!==""||F.rmax!=="") n++; if(F.rsimin!==""||F.rsimax!=="") n++;
  if(F.cap) n++; if(F.news) n++; if(F.macro) n++; n += F.good.length?1:0; n += F.bad.length?1:0; n += F.tags.length?1:0; return n; }
function passes(r, F){
  if (F.sig.length){ const sg = r.signal||"NONE"; if(!F.sig.includes(sg)) return false; }
  if (F.sec.length && !F.sec.includes(r.sector)) return false;
  if (num(F.smin)!=null && r.score < num(F.smin)) return false;
  if (num(F.smax)!=null && r.score > num(F.smax)) return false;
  for (const [k,v] of Object.entries(F.parts)) if (v>0 && (r.parts[k]??0) < v) return false;
  const vq = {value:r.vq?.[0], quality:r.vq?.[1], growth:r.vq?.[2]};
  for (const [k,v] of Object.entries(F.vqmin)) if (v>0 && (vq[k]??0) < v) return false;
  if (num(F.pemin)!=null && !(r.pe!=null && r.pe >= num(F.pemin))) return false;
  if (num(F.pemax)!=null && !(r.pe!=null && r.pe > 0 && r.pe <= num(F.pemax))) return false;
  if (num(F.rmin)!=null && !(r.ret3m!=null && r.ret3m >= num(F.rmin))) return false;
  if (num(F.rmax)!=null && !(r.ret3m!=null && r.ret3m <= num(F.rmax))) return false;
  if (num(F.rsimin)!=null && !(r.rsi!=null && r.rsi >= num(F.rsimin))) return false;
  if (num(F.rsimax)!=null && !(r.rsi!=null && r.rsi <= num(F.rsimax))) return false;
  if (F.cap){ const c = Number(F.cap); if (c>0 ? !(r.mcap>=c) : !(r.mcap!=null && r.mcap < -c)) return false; }
  if (F.news==="pos" && !(r.ns>0.05)) return false;
  if (F.news==="notneg" && !(r.ns==null || r.ns>=0)) return false;
  if (F.news==="neg" && !(r.ns<-0.05)) return false;
  if (F.news==="has" && r.ns==null) return false;
  if (F.macro==="tail" && !(r.ms>=0.1)) return false;
  if (F.macro==="nohead" && !(r.ms==null || r.ms>-0.1)) return false;
  if (F.macro==="head" && !(r.ms<=-0.1)) return false;
  const ev = r.events||[];
  if (F.good.length && !F.good.some(e=>ev.includes(e))) return false;
  if (F.bad.length && F.bad.some(e=>ev.includes(e))) return false;
  if (F.tags.length && !F.tags.every(t=>(r.reasons||[]).includes(t))) return false;
  return true;
}
function pills(group, opts, sel, neg){ return `<div class="pills">${opts.map(([v,l])=>`<button class="pill ${neg?"neg":""} ${sel.includes(v)?"on":""}" onclick="tog('${group}','${String(v).replace(/'/g,"\\'")}')">${esc(l)}</button>`).join("")}</div>`; }
function one(group, opts, cur){ return `<div class="pills">${opts.map(([v,l])=>`<button class="pill ${cur===v?"on":""}" onclick="setF('${group}', ${JSON.stringify(v).replace(/"/g,"&quot;")})">${esc(l)}</button>`).join("")}</div>`; }
function rng(a,b,ph1,ph2){ const F=getF(); return `<div class="rangerow"><input inputmode="decimal" placeholder="${ph1}" value="${esc(F[a])}" onchange="setF('${a}', this.value)"><span class="mute">to</span><input inputmode="decimal" placeholder="${ph2}" value="${esc(F[b])}" onchange="setF('${b}', this.value)"></div>`; }
function drawPanel(){
  const F = getF(), rows = D.markets[M]||[];
  const secs = [...new Set(rows.map(r=>r.sector).filter(Boolean))].sort();
  const evs = [...new Set(rows.flatMap(r=>r.events||[]))];
  const good = evs.filter(e=>!BAD.includes(e)).sort(), bad = evs.filter(e=>BAD.includes(e)).sort();
  const tags = [...new Set(rows.flatMap(r=>r.reasons||[]))].filter(t=>!evs.includes(t)).sort();
  const caps = M==="US" ? [["",'Any'],["1e10",">$10B"],["5e10",">$50B"],["2e11",">$200B"],["-2e10","<$20B"]]
             : M==="ASX" ? [["",'Any'],["2e9",">A$2B"],["1e10",">A$10B"],["5e10",">A$50B"],["-5e9","<A$5B"]]
             : [["",'Any'],["5e10",">PKR 50B"],["2e11",">PKR 200B"],["5e11",">PKR 500B"],["-5e10","<PKR 50B"]];
  $("fpanel").innerHTML = `
   <div class="fg"><span class="fl">Signal</span>${pills("sig",[["BUY","BUY"],["WATCH","WATCH"],["NONE","No signal"]],F.sig)}
     <div class="mute" style="margin-top:4px">Tap BUY + WATCH for both.</div></div>
   <div class="fg"><span class="fl">Sector</span>${pills("sec",secs.map(x=>[x,x]),F.sec)}</div>
   <div class="fg"><span class="fl">Overall score</span>${rng("smin","smax","min e.g. 60","max")}</div>
   <div class="fg"><span class="fl">Minimum part scores (0–100 rank)</span>
     ${PARTS.map(([k,l])=>`<div class="sl"><span>${l}</span><input type="range" min="0" max="95" step="5" value="${F.parts[k]||0}" oninput="this.nextElementSibling.textContent=this.value" onchange="F_part('${k}',this.value)"><b>${F.parts[k]||0}</b></div>`).join("")}
     ${[["value","Value vs sector"],["quality","Quality"],["growth","Growth"]].map(([k,l])=>`<div class="sl"><span>${l}</span><input type="range" min="0" max="95" step="5" value="${F.vqmin[k]||0}" oninput="this.nextElementSibling.textContent=this.value" onchange="F_vq('${k}',this.value)"><b>${F.vqmin[k]||0}</b></div>`).join("")}</div>
   <div class="fg"><span class="fl">Company news</span>${one("news",[["","Any"],["pos","Positive"],["notneg","Not negative"],["neg","Negative"],["has","Has news"]],F.news)}</div>
   <div class="fg"><span class="fl">Sector & politics</span>${one("macro",[["","Any"],["tail","Tailwind"],["nohead","No headwind"],["head","Headwind"]],F.macro)}</div>
   ${good.length?`<div class="fg"><span class="fl">Has a recent event (any of)</span>${pills("good",good.map(x=>[x,x]),F.good)}</div>`:""}
   ${bad.length?`<div class="fg"><span class="fl">Exclude stocks with</span>${pills("bad",bad.map(x=>[x,x]),F.bad,true)}</div>`:""}
   <div class="fg"><span class="fl">P/E</span>${rng("pemin","pemax","min","max e.g. 20")}</div>
   <div class="fg"><span class="fl">3-month return %</span>${rng("rmin","rmax","min e.g. 0","max")}</div>
   <div class="fg"><span class="fl">RSI (14 day)</span>${rng("rsimin","rsimax","min","max e.g. 70")}<div class="mute" style="margin-top:4px">Under 30 = oversold, over 70 = overbought.</div></div>
   <div class="fg"><span class="fl">Market cap</span>${one("cap",caps,F.cap)}</div>
   ${tags.length?`<div class="fg"><span class="fl">Must have all of these tags</span>${pills("tags",tags.map(x=>[x,x]),F.tags)}</div>`:""}
   <div class="fg"><label>Sort by</label><select onchange="setF('sort',this.value)">${Object.entries(SORTS).map(([k,v])=>`<option value="${k}" ${F.sort===k?"selected":""}>${v.l}</option>`).join("")}</select></div>
   <div class="fact"><button onclick="resetF()">Clear all</button><button class="pri" onclick="$('fpanel').classList.remove('open');window.scrollTo({top:$('count').offsetTop-60,behavior:'smooth'})">Show ${(D.markets[M]||[]).filter(r=>passes(r,F)).length} stocks</button></div>`;
}
function tog(g,v){ const F=getF(); const a=F[g]; const i=a.indexOf(v); i>=0?a.splice(i,1):a.push(v); saveF(); render(); }
function setF(k,v){ const F=getF(); F[k]=v; saveF(); render(); }
function F_part(k,v){ getF().parts[k]=Number(v); saveF(); render(); }
function F_vq(k,v){ getF().vqmin[k]=Number(v); saveF(); render(); }
function resetF(){ FS[M]=DEF(); saveF(); render(); }
$("fbtn").onclick = ()=>{ $("fpanel").classList.toggle("open"); render(); };
$("freset").onclick = resetF;
$("sortbtn").onclick = ()=>{ const ks=Object.keys(SORTS), F=getF(); F.sort = ks[(ks.indexOf(F.sort)+1)%ks.length]; saveF(); render(); };

/* ---------------- market clock ---------------- */
const MK = {
  US:  {tz:"America/New_York", city:"New York", s:{1:[[570,960]],2:[[570,960]],3:[[570,960]],4:[[570,960]],5:[[570,960]]}},
  ASX: {tz:"Australia/Sydney", city:"Sydney", s:{1:[[600,960]],2:[[600,960]],3:[[600,960]],4:[[600,960]],5:[[600,960]]}},
  PSX: {tz:"Asia/Karachi", city:"Karachi", s:{1:[[570,930]],2:[[570,930]],3:[[570,930]],4:[[570,930]],5:[[555,720],[870,990]]}},
};
const WD = {Sun:0,Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6};
function tzParts(d, tz){ const p = {}; new Intl.DateTimeFormat("en-US",{timeZone:tz,weekday:"short",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(d).forEach(x=>p[x.type]=x.value); return {wd:WD[p.weekday], min:(+p.hour)*60+(+p.minute)}; }
function isOpen(m, d){ const t = tzParts(d, MK[m].tz); return (MK[m].s[t.wd]||[]).some(([a,b])=>t.min>=a && t.min<b); }
function fmtDur(ms){ const m = Math.round(ms/60000), d = Math.floor(m/1440), h = Math.floor((m%1440)/60), mm = m%60; return (d?d+"d ":"") + (d||h?h+"h ":"") + mm+"m"; }
function clockTick(){
  const m = MK[M]; if(!m){ $("clock").innerHTML=""; return; }
  const now = new Date(), open = isOpen(M, now);
  let t = new Date(now); t.setSeconds(0,0);
  for (let i=0;i<60*24*8;i++){ t = new Date(t.getTime()+60000); if (isOpen(M,t)!==open) break; }
  const local = now.toLocaleTimeString("en-AU",{timeZone:m.tz,hour:"numeric",minute:"2-digit",weekday:"short"});
  const when = t.toLocaleString(undefined,{weekday:"short",hour:"numeric",minute:"2-digit"});
  $("clock").innerHTML = `<div><b>${M}</b> · ${m.city} ${local}<div class="mute">${open?"Closes":"Opens"} in ${fmtDur(t-now)} (${when} your time)</div></div><span class="st ${open?"open":"closed"}">${open?"● OPEN":"● CLOSED"}</span>`;
}
setInterval(clockTick, 30000);
render();

$("more").onclick = ()=>{ showAll=!showAll; render(); };
$("q").oninput = render;
Object.keys(D.markets).forEach(m=>{const b=document.createElement("button");b.textContent=m;b.onclick=()=>{M=m;showAll=false;$("q").value="";render()};$("tabs").appendChild(b)});

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
    <div style="margin-top:8px">Price <b>${d.price??"–"}${d.market==="PSX"?" PKR":""}</b> · Market cap <b>${fmtCap(d.mcap)}${d.market==="PSX"?" PKR":""}</b></div></div>
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
    ${d.events&&d.events.length?`<div class="chips" style="margin:0 0 8px">${d.events.map(e=>`<span class="chip ${e.impact<0?"bad":""}">${e.impact>0?"▲":e.impact<0?"▼":"•"} ${esc(e.label)}</span>`).join("")}</div>`:""}
    <div class="mute" style="margin-bottom:6px">Recency-weighted sentiment: <b style="color:${sentColor(d.news_avg)}">${d.news_avg??0}</b> · competitors: <b style="color:${sentColor(d.peer_avg)}">${d.peer_avg??0}</b>${d.macro_share>0?` · ${Math.round(d.macro_share*100)}% about policy/macro`:""}</div>
    ${d.news.length ? d.news.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}
      <div class="mute">${esc(n.publisher||"")}${n.quality==="promo"?" (promotional, half weight)":""} ${n.date||""}${n.macro?" · policy/macro":""}${(n.events||[]).map(e=>` · <b style="color:${BAD.includes(e)?"var(--neg)":"var(--acc)"}">${esc(e)}</b>`).join("")}</div></div>`).join("") : `<div class="mute">No recent headlines.</div>`}</div>

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
    from events import BAD
    page = PAGE.replace("__BAD_EVENTS__", ",".join(json.dumps(b) for b in sorted(BAD)))
    with open(path, "w") as f:
        f.write(page.replace("__DATA__", json.dumps(payload, default=str, separators=(",", ":"))))
