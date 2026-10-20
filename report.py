"""Writes the mobile-friendly web page. Per-stock details load from docs/stocks/<TICKER>.json."""
import json

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Screener</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1c1a;--mute:#6b6a65;--line:#e4e2dc;--acc:#2f6f4f;--neg:#b0432c;--chip:#eef3ef;--ma50:#c9822b;--ma200:#5b6fb5;--idx:#9a988f}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--mute:#9a988f;--line:#2e2d2a;--acc:#6fbf93;--neg:#e08a74;--chip:#24302a;--ma50:#e0a75c;--ma200:#8fa0e0;--idx:#77756e}}
*{box-sizing:border-box;min-width:0}html,body{overflow-x:hidden;margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,Segoe UI,sans-serif;-webkit-text-size-adjust:100%}
button{font:inherit;color:inherit}
header{padding:20px 16px 8px}h1{font-size:22px;margin:0}.sub{color:var(--mute);font-size:13px;margin-top:4px}
.tabs{display:flex;gap:8px;padding:8px 16px;position:sticky;top:0;background:var(--bg);z-index:2}
.tabs button{flex:1;padding:10px;border:1px solid var(--line);background:var(--card);border-radius:10px;font-weight:600}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.tabs button{flex:1 1 auto;padding:10px 6px;font-size:13px;min-width:0;white-space:nowrap}
.subtabs{display:flex;gap:6px;padding:0 16px 8px;position:sticky;top:57px;background:var(--bg);z-index:2}
.subtabs button{flex:1;padding:7px;border:1px solid var(--line);background:var(--card);border-radius:20px;font-weight:600;font-size:13px}
.subtabs button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
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
.sig.HOLD{border:1px solid var(--line);color:var(--mute);font-weight:600}
.sig.AVOID{border:1px solid var(--ma50);color:var(--ma50)}.sig.SELL{background:var(--neg);color:#fff}
.sig.HALAL{border:1px solid #3a9d6b;color:#3a9d6b}.sig.HDOUBT{border:1px dashed var(--mute);color:var(--mute);font-weight:600}
.sig.flag{border:1px dashed var(--mute);color:var(--ink);font-weight:600}
.card.SELL{border:2px solid var(--neg)}
.chip.good-chip{background:var(--acc);color:#fff}.chip.halal-chip{border:1px solid #3a9d6b;color:#3a9d6b;background:none}.chip.div-chip{border:1px solid #b08a2e;color:#b08a2e;background:none}
.dbar{display:flex;align-items:flex-end;gap:6px;height:90px;margin:10px 0 2px}.dbar div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;font-size:10px;color:var(--mute);height:100%}
.dbar i{display:block;width:100%;background:#b08a2e;border-radius:3px 3px 0 0;min-height:2px}.dbar i.part{opacity:.45}
details.why{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px}
details.why summary{cursor:pointer;color:var(--acc);font-size:13px;font-weight:600;list-style:none}
details.why summary::before{content:"ⓘ  "}
details.why p{margin:8px 0 0;font-size:14px;line-height:1.55}
details.why ul{margin:6px 0 0;padding-left:18px;font-size:14px;line-height:1.55}
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
.perf{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin:6px 0 10px}
.perf div{text-align:center;padding:6px 2px;border-radius:8px;background:var(--bg)}
.perf small{display:block;font-size:11px;color:var(--mute)}.perf b{font-size:13px}
.heat{width:100%;border-collapse:separate;border-spacing:2px;font-size:12px}
.heat th{font-weight:500;color:var(--mute);font-size:11px;padding:2px;text-align:center}
.heat td{padding:6px 3px;text-align:center;border-radius:5px;border:0}
.heatwrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -4px}
.heat td,.heat th{min-width:46px}
.heat td:first-child,.heat th:first-child{position:sticky;left:0;z-index:1;background:var(--card);min-width:96px;max-width:96px}
.heat td:first-child{text-align:left;padding-left:4px;font-size:12px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mine-head{margin:10px 16px 0;padding:12px;border-radius:12px;background:var(--card);border:1px solid var(--line)}
.btnrow{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.sbtn{padding:7px 11px;border-radius:9px;border:1px solid var(--line);background:var(--bg);font-size:13px;font-weight:600}
.sbtn.pri{background:var(--acc);border-color:var(--acc);color:#fff}.sbtn.neg{color:var(--neg)}
.trade{margin:10px 16px;padding:14px;border-radius:14px;background:var(--card);border:1px solid var(--line)}
.trade .row{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.big2{font-size:20px;font-weight:700}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:20;display:flex;align-items:flex-end;justify-content:center}
.modal .mbox{background:var(--card);width:100%;max-width:520px;border-radius:16px 16px 0 0;padding:16px 16px 28px;max-height:80vh;overflow:auto}
.modal input,.modal textarea{width:100%;padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:16px;margin:6px 0}
.logrow{padding:8px 0;border-top:1px solid var(--line);font-size:13px}.logrow:first-child{border-top:0}
.st-ok{color:var(--acc)}.st-warnings{color:var(--ma50)}.st-failed{color:var(--neg)}
.cardx{float:right;margin:-6px -6px 0 8px;border:0;background:none;color:var(--mute);font-size:18px;padding:4px 8px}
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
<div class="subtabs" id="subtabs"></div>
<div class="clock" id="clock"></div>
<details class="box" id="ovbox" open><summary><b style="color:var(--ink)">Market overview</b> <span id="ovsum"></span></summary><div id="ov" style="margin-top:8px"></div></details>
<input class="search" id="q" placeholder="Search (e.g. CBA, Apple, OGDC, Gold, Bitcoin)" autocomplete="off">

<details class="box" id="macrobox"><summary><b style="color:var(--ink)">Market &amp; politics today</b> <span id="macrosum"></span></summary><div id="macro" style="margin-top:8px"></div></details>
<details class="box" id="statsbox"><summary>How reliable is this? (labels, scorecard, backtest)</summary><div id="stats" style="margin-top:8px"></div></details>
<div id="mine"></div>
<div class="fbar"><button id="fbtn">Filters</button><button id="sortbtn" style="flex:1;text-align:left"></button><button id="freset" style="display:none">Clear</button></div>
<div id="fpanel"></div>
<div class="count" id="count"></div>
<div id="list"></div><button class="more" id="more"></button>
<details class="box" id="logbox"><summary>Run log <span id="logsum"></span></summary><div id="runlog" style="margin-top:8px"></div></details>
<footer>Ranks stocks by blending a price-trend model, fundamentals vs sector peers, and news sentiment for the company and its competitors. Scores are relative rankings, not price targets. Not financial advice — paper-trade first.</footer>
<div id="sheet"></div>
<script>
const D = __DATA__;
const BAD = ["Negative news","Sector headwind","Overbought (RSI)","Macro headwind",__BAD_EVENTS__];
const L = {ml:"Model",fundamental:"Fundam.",news:"News",peers:"Peers",macro:"Macro"};
let M = Object.keys(D.markets)[0], showAll = false;
const $ = id => document.getElementById(id);
const tk = t => t.replace(".AX","").replace(".KA","").replace("=F","").replace(/(\d{3,})?-USD$/,"");
const CUR = m => (D.stats[m]||{}).currency || {US:"USD",ASX:"AUD",PSX:"PKR",COM:"USD",CRYPTO:"USD"}[m] || "";
/* Commodities & crypto ("assets") have no company accounts: no fundamentals, health, dividends, P/E */
const ASSET = m => m==="COM" || m==="CRYPTO";
const MNAME = m => ({COM:"Commodities", CRYPTO:"Crypto"})[m] || m;
const NOUN = m => m==="COM" ? "commodities" : m==="CRYPTO" ? "coins" : "stocks";
const pct = (v,d=1) => v==null ? "–" : (v>0?"+":"") + (v*100).toFixed(d) + "%";
const esc = s => String(s??"").replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
/* Each market is updated at its own time (after its close) — show the open tab's update time */
function updGen(){
  const u = D.updated||{}, mk = Object.keys(D.markets).includes(M) ? M : null;
  const fmt = x => new Date(x).toLocaleString(undefined,{weekday:"short",day:"numeric",month:"short",hour:"numeric",minute:"2-digit",timeZoneName:"short"});
  $("gen").textContent = (mk ? `${MNAME(mk)} updated ${fmt(u[mk]||D.generated)}` : "Updated " + fmt(D.generated)) + (D.demo ? " · DEMO DATA" : "");
}

function badge(sg){ return sg ? `<span class="sig ${sg}">${sg}</span>` : ""; }
/* Stocks you hold in Paper (open trades) */
function owned(t){ return PT.get().some(x=>x.ticker===t && x.status==="open"); }
/* Main label: BUY / WATCH / AVOID — or HOLD / SELL if you already own it in Paper */
function mainLabel(r){
  const sg = r.signal||"HOLD", hz = r.hz||["","",""], bad = sg==="SELL"||sg==="AVOID";
  if (owned(r.ticker)) return bad ? "SELL" : "HOLD";
  if (bad) return "AVOID";
  if (hz.includes("BUY")) return "BUY";
  if (hz.includes("WATCH") || sg==="WATCH") return "WATCH";
  return "";
}
/* Sub-labels shown with the other tags */
function subTags(r){
  const hz = r.hz||["","",""], names = ["Short-term","Medium-term","Long-term"], out = [];
  hz.forEach((v,i)=>{ if(v==="BUY") out.push(`<span class="chip good-chip">${names[i]} buy</span>`); });
  hz.forEach((v,i)=>{ if(v==="WATCH") out.push(`<span class="chip">${names[i]} watch</span>`); });
  if (r.hl==="HALAL") out.push(`<span class="chip halal-chip">Halal</span>`);
  (r.dv||[]).forEach(t=>out.push(t==="Dividend at risk" ? `<span class="chip bad">${t}</span>` : `<span class="chip div-chip">${t}${t!=="Dividend grower"&&r.dy!=null?` ${r.dy.toFixed(1)}%`:""}</span>`));
  if (r.wk || r.weakening) out.push(`<span class="chip bad">Weakening</span>`);
  (r.flags||[]).forEach(f=>out.push(`<span class="chip">${f==="REBOUND"?"Rebound candidate":"Take profit?"}</span>`));
  return out.join("");
}
const LABEL_INFO = {
  BUY:"passes every buy check for at least one time horizon (see the tags)", WATCH:"one check short of a buy",
  "":"no strong reason to buy or avoid right now", HOLD:"you hold this in Paper and there's no reason to sell",
  AVOID:"recent red flag or weak on every front — don't buy now", SELL:"you hold this in Paper and it now has a red flag or fails on every front — consider selling"};
function normTicker(q, m){
  let t = q.trim().toUpperCase().replace(/^(ASX|NYSE|NASDAQ|PSX|KSE):/, "").replace(/\s+/g, "");
  if (m==="ASX") return t.replace(/\.AX$/,"") + ".AX";
  if (m==="PSX") return t.replace(/\.KA$/,"") + ".KA";
  return t.replace(/\./g, "-");
}
function analyseBox(q){
  if (ASSET(M)) return `<div class="box mute">No match in ${MNAME(M)}. ${M==="CRYPTO"?"The screener covers the top 50 coins by size (stablecoins left out).":"The screener covers about 20 major commodities."}</div>`;
  const looks = /^[A-Za-z0-9.:-]{1,14}$/.test(q.trim());
  if (!looks) return `<div class="box mute">No match in ${M}. To analyse a stock that isn't in the screener, search by its <b>ticker</b> (e.g. PLS, ZIP, SOFI, SYS).</div>`;
  const t = normTicker(q, M), st = (EXTRAS.items||{})[t];
  const status = st ? (st.status==="not_found" ? `<div class="bad" style="margin-top:6px">${esc(tk(t))} wasn't found on Yahoo Finance as a ${M} stock. Check the ticker or try another market.</div>`
      : st.status==="waiting" ? `<div class="mute" style="margin-top:6px">Queued — it will be analysed in the next daily run.</div>` : "") : "";
  return `<div class="box"><b>${esc(tk(t))}</b> isn't in the screener.<div class="mute" style="margin-top:4px">Analyse it on demand — full score, labels, checks, financial health, halal and news, ranked against the ${M} market. Usually ready in about 15–20 minutes, then updated every day.</div>
    <div class="btnrow">${["US","ASX","PSX"].map(m=>`<button class="sbtn ${m===M?"pri":""}" onclick="requestAnalysis('${esc(q.trim())}','${m}')">Analyse as ${m}: ${esc(tk(normTicker(q,m)))}</button>`).join("")}</div>${status}</div>`;
}
async function requestAnalysis(q, m){
  const t = normTicker(q, m);
  if (DBSTATE !== "ready") { alert("Please sign in first (Lists tab), so the request is saved to your account."); M="Lists"; render(); return; }
  const { error } = await SB.from("tracked_stocks").insert({ticker:t, market:m});
  if (error && !/duplicate|unique/i.test(error.message)) return alert("Couldn't request it: " + error.message);
  TRACKED = null;
  alert(`${tk(t)} requested. It's usually ready in about 15–20 minutes — find it in Lists → Requested, or search for it again.`);
  pollExtras(); render();
}
let POLL = null;
function pollExtras(){ if (POLL) return; POLL = setInterval(()=>{ loadExtras(); if (!(TRACKED||[]).some(x=>!ALL[x.ticker] && !((EXTRAS.items||{})[x.ticker]||{}).status)) { clearInterval(POLL); POLL=null; } }, 60000); }
function card(r, i, extra=""){
  return `<div class="card ${mainLabel(r)}" onclick="openStock('${r.ticker}')">${extra}<div class="top"><div style="min-width:0"><span class="rank">${MINE(M)||r.extra?MNAME(r.market)+" ":""}#${(r.rank||i+1)}</span><span class="tk">${tk(r.ticker)}</span>${badge(mainLabel(r))}
   <div class="nm">${esc(r.name)} · ${esc(r.sector)}</div></div><div class="sc">${r.score}</div></div>
   <div class="bars">${Object.entries(r.parts).map(([k,v])=>`<div class="bar"><small>${L[k]}</small><i><span style="width:${v}%"></span></i></div>`).join("")}</div>
   <div class="meta">${CUR(r.market||M)} ${r.price??"–"} · 3m ${r.ret3m??"–"}%${ASSET(r.market||M)?(r.mcap?` · mkt cap ${fmtCap(r.mcap)}`:""):` · P/E ${r.pe??"–"}`}</div>
   <div class="chips">${subTags(r)}${r.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div></div>`;
}
function render(){
  try{ updGen(); }catch(e){}
  if (STOCKS.includes(M)) LASTSTOCK = M;
  [...$("tabs").children].forEach(b=>b.classList.toggle("on", b.dataset.k===TOP(M)));
  $("subtabs").style.display = STOCKS.includes(M) ? "" : "none";
  [...$("subtabs").children].forEach(b=>b.classList.toggle("on", b.dataset.k===M));
  const mine = MINE(M);
  ["clock","ovbox","macrobox","statsbox"].forEach(id=>$(id).style.display = mine ? "none" : "");
  $("mine").style.display = mine ? "" : "none";
  renderLog();
  if (mine) return renderMine();
  const s = D.stats[M]||{}, rows = rowsFor(M);
  const buys = rows.filter(r=>r.signal==="BUY"), watch = rows.filter(r=>r.signal==="WATCH");
  const nHalal = rows.filter(r=>r.hl==="HALAL").length;
  const sbuy = rows.filter(r=>(r.hz||[])[0]==="BUY"), lbuy = rows.filter(r=>(r.hz||[])[2]==="BUY");
  const sells = rows.filter(r=>r.signal==="SELL"), avoids = rows.filter(r=>r.signal==="AVOID");
  const reb = rows.filter(r=>(r.flags||[]).includes("REBOUND")), tp = rows.filter(r=>(r.flags||[]).includes("TAKE PROFIT"));
  const T = s.track||{};
  const trl = lab => T[lab] ? `${lab}: ${T[lab].n} past calls, right <b>${Math.round(T[lab].win_rate*100)}%</b> of the time (avg ${(T[lab].avg_excess*100).toFixed(2)}% vs index)` : null;
  const trl2 = (lab, name) => T[lab] ? `${name}: ${T[lab].n} past calls, right <b>${Math.round(T[lab].win_rate*100)}%</b> of the time (avg ${(T[lab].avg_excess*100).toFixed(2)}% vs index)` : null;
  const trs = [["SHORT BUY","Short-term buys"],["BUY","Medium-term buys"],["LONG BUY","Long-term buys"],["AVOID","Avoids"],["SELL","Weak-on-every-front"]].map(([a,b])=>trl2(a,b)).filter(Boolean);
  const link = r => `<a href="#" onclick="openStock('${r.ticker}');return false" style="color:inherit">${tk(r.ticker)}</a>`;
  const tr = trs.length ? trs.join("; ") + "." : `building — check back in a week or two.`;
  const labelHelp = `<details class="why" open><summary>What do the labels mean?</summary><ul>
        <li><b>BUY</b> — passes every buy check for at least one time horizon. The tags say which: <b>Short-term buy</b> (days–weeks: momentum, fresh positive news, above the 50-day average, RSI 50–70, rising interest), <b>Medium-term buy</b> (1–6 months: top 15% score, uptrend, not overbought, solid fundamentals, no bad news or headwind${s.model_used ? ", price model agrees" : ""}), <b>Long-term buy</b> (1 year+: top fundamentals, F-score 7+, no bankruptcy risk, fairly priced, high quality, long-term uptrend).</li>
        <li><b>WATCH</b> — one check short of a buy.</li>
        <li><b>AVOID</b> — a red flag in the last 10 days (scandal/probe, profit warning, capital raising, CEO exit, debt stress…), a strong sector/political headwind, or weak on every front.</li>
        <li>No badge — nothing notable either way.</li>
        <li><b>HOLD / SELL</b> — only for stocks you hold in Paper: SELL when a red flag appears or it turns weak on every front, otherwise HOLD.</li>
        <li>Tags: <b>Halal</b> passes the Shariah screen; <b>Rebound candidate</b> = good company that looks oversold; <b>Take profit?</b> = big run, overheated, support fading.</li></ul></details>`;
  const scoreLine = `<div style="margin:8px 0"><b>Scorecard:</b> ${tr}</div>`;
  $("stats").innerHTML = s.error ? `<b class="bad">${M} run failed: ${esc(s.error)}</b>` : labelHelp + scoreLine +
    `<b>Backtest:</b> tested on ${s.test_from} onwards (data the model never saw): top-20% picks beat bottom-20% by <b>${((s.top_minus_bottom||0)*100).toFixed(2)}%</b> a month; ranking accuracy (IC) <b>${s.ic_mean}</b> (0 = random); top picks beat the index <b>${Math.round((s.top_hit_rate||0)*100)}%</b> of the time. ${s.screened} stocks passed the screen.<br><br><b>Data check:</b> prices up to the ${s.price_date||"–"} close (holidays not shown on the clock); ${Math.round((s.news_coverage||0)*100)}% of stocks had news in the last 10 days (scored by ${s.news_method}). AI scoring: <b>${s.ai_scoring==="on"||s.ai_scoring===true?"on":s.ai_scoring==="failed"?"FAILED today (out of API credit or key problem) — using free rules":"off — add an ANTHROPIC_API_KEY secret to turn it on"}</b>.${(s.news_coverage||0)<0.5?" <b>News coverage is low — treat the News and Peers parts with caution.</b>":""}`
    + (s.model_used===false ? " <b>The price model failed this test here, so it counts for only 10%.</b>" : "");
  renderOverview(s);
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
  $("list").innerHTML = shown.map(([r,i])=>card(r,i)).join("") || (q && !active ? analyseBox(q) : `<div class="box mute">No stocks match. Try loosening the filters.</div>`);
  $("more").style.display = q || active || rows.length <= D.top_n ? "none" : "block";
  $("more").textContent = showAll ? `Show top ${D.top_n} only` : `Show all ${rows.length} ranked stocks`;
  $("fbtn").textContent = active ? `Filters (${active})` : "Filters";
  $("fbtn").classList.toggle("on", !!active);
  $("freset").style.display = active ? "block" : "none";
  $("sortbtn").textContent = "Sort: " + SORTS[key].l;
  if ($("fpanel").classList.contains("open")) drawPanel();
  clockTick();
}

/* ---------------- my watchlists & paper trades (saved on this device) ---------------- */
function store(key, def){ return {
  get(){ if(!this.v){ try{ this.v = JSON.parse(localStorage.getItem(key)) || def(); }catch(e){ this.v = def(); } } return this.v; },
  save(){ try{ localStorage.setItem(key, JSON.stringify(this.v)); }catch(e){ alert("Couldn't save on this device (private browsing?)"); } } }; }
const WL = store("watchlists", ()=>({lists:{"My watchlist":[]}, cur:"My watchlist"}));
const PT = store("paper_trades", ()=>[]);

/* ---- account database (Supabase). Local storage is only a cache until you sign in. ---- */
let SB = null, USER = null, DBSTATE = "off";   // off | signedout | loading | ready | error
const DBCFG = D.db || {};
function dbInit(){
  if (!DBCFG.url || !DBCFG.key) return;
  DBSTATE = "signedout";
  const sc = document.createElement("script");
  sc.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";
  sc.onload = async () => {
    const linkErr = new URLSearchParams(location.hash.slice(1)).get("error_description");
    SB = supabase.createClient(DBCFG.url, DBCFG.key, {auth:{persistSession:true, detectSessionInUrl:true, flowType:"implicit", autoRefreshToken:true}});
    if (linkErr) { DBERR = "Sign-in link didn't work: " + linkErr.replace(/\+/g," ") + ". Request a new link (each link works once)."; }
    SB.auth.onAuthStateChange((ev, sess) => { const u = sess?.user || null; if ((u&&u.id) !== (USER&&USER.id)) { USER = u; dbLoad(); } });
    const { data } = await SB.auth.getSession(); USER = data.session?.user || null;
    if (AUTH_HASH) { history.replaceState(null, "", location.pathname); if (USER) { M = "Lists"; } }
    dbLoad();
  };
  sc.onerror = () => { DBSTATE = "error"; DBERR = "couldn't load the database library — check your internet connection"; render(); };
  document.head.appendChild(sc);
}
const toRow = x => ({id:x.id, ticker:x.ticker, market:x.market, currency:x.currency||CUR(x.market), entry_date:x.date, entry_price:x.price,
  entry_idx:x.idx, label:x.label, hz:x.hz, flags:x.flags, score:x.score, amount:x.amount, shares:x.shares, note:x.note, status:x.status,
  exit_date:x.exit_date||null, exit_price:x.exit_price??null, exit_idx:x.exit_idx??null, exit_label:x.exit_label||null});
const fromRow = r => ({id:Number(r.id), ticker:r.ticker, market:r.market, currency:r.currency, date:r.entry_date, price:Number(r.entry_price),
  idx:r.entry_idx!=null?Number(r.entry_idx):null, label:r.label, hz:r.hz||["","",""], flags:r.flags||[], score:Number(r.score), amount:Number(r.amount),
  shares:Number(r.shares), note:r.note||"", status:r.status, exit_date:r.exit_date, exit_price:r.exit_price!=null?Number(r.exit_price):null,
  exit_idx:r.exit_idx!=null?Number(r.exit_idx):null, exit_label:r.exit_label});
async function dbLoad(){
  if (!SB) return;
  if (!USER){ DBSTATE = "signedout"; render(); return; }
  DBSTATE = "loading"; render();
  try {
    const [w, t] = await Promise.all([SB.from("watchlists").select("*"), SB.from("paper_trades").select("*").order("id",{ascending:false})]);
    if (w.error) throw w.error; if (t.error) throw t.error;
    // First sign-in on this device: move anything saved locally into the account
    const localW = WL.get(), localT = PT.get();
    const hasLocal = Object.values(localW.lists).some(a=>a.length) || localT.length;
    if (hasLocal && !localStorage.getItem("migrated_"+USER.id)) {
      const remoteNames = new Set(w.data.map(r=>r.name));
      const up = Object.entries(localW.lists).filter(([n,a])=>a.length).map(([n,a])=>{ const r = w.data.find(z=>z.name===n); return {name:n, tickers:[...new Set([...(r?.tickers||[]), ...a])]}; });
      if (up.length) await SB.from("watchlists").upsert(up, {onConflict:"user_id,name"});
      if (localT.length) await SB.from("paper_trades").upsert(localT.map(toRow), {onConflict:"id"});
      try { localStorage.setItem("migrated_"+USER.id, "1"); } catch(e){}
      return dbLoad();
    }
    const cur = WL.get().cur;
    WL.v = {lists: Object.fromEntries(w.data.map(r=>[r.name, r.tickers||[]])), cur};
    if (!Object.keys(WL.v.lists).length) WL.v.lists["My watchlist"] = [];
    if (!WL.v.lists[cur]) WL.v.cur = Object.keys(WL.v.lists)[0];
    PT.v = t.data.map(fromRow);
    WL.save(); PT.save();
    DBSTATE = "ready"; TRACKED = null;
  } catch(e) { console.error(e); DBSTATE = "error"; DBERR = e.message || String(e); }
  render();
}
let DBERR = "";
async function dbRun(fn){ if (DBSTATE!=="ready") return; try { const r = await fn(); if (r && r.error) throw r.error; } catch(e){ DBERR = e.message||String(e); alert("Couldn't save to your account: "+DBERR); } }
const dbList = n => dbRun(()=>SB.from("watchlists").upsert({name:n, tickers:WL.get().lists[n]||[], updated_at:new Date().toISOString()}, {onConflict:"user_id,name"}));
const dbListDel = n => dbRun(()=>SB.from("watchlists").delete().eq("name", n));
const dbTrade = x => dbRun(()=>SB.from("paper_trades").upsert(toRow(x), {onConflict:"id"}));
const dbTradeDel = id => dbRun(()=>SB.from("paper_trades").delete().eq("id", id));
async function signIn(){
  const email = ($("em")?.value||"").trim(); if(!email) return;
  const { error } = await SB.auth.signInWithOtp({email, options:{emailRedirectTo: location.origin + location.pathname}});
  if (error) return alert("Sign-in failed: " + error.message);
  $("acct").innerHTML = `<div>Check <b>${esc(email)}</b> and tap the link <b>once</b>. If your email app opens it in its own browser, long-press the link and choose “Open in Safari/Chrome” instead, so you're signed in where you use this page.</div>`;
}
async function signInPw(){
  const email = ($("em")?.value||"").trim(), password = $("pw")?.value||"";
  if (!email || !password) return alert("Enter your email and password.");
  const { data, error } = await SB.auth.signInWithPassword({email, password});
  if (error) return alert(error.message.includes("Invalid") ? "Wrong email or password. If you haven't set a password yet, use the email link first." : "Sign-in failed: " + error.message);
  USER = data.user; dbLoad();
}
async function setPassword(){
  const pw = prompt("Choose a password (at least 8 characters):"); if (!pw) return;
  if (pw.length < 8) return alert("Please use at least 8 characters.");
  const { error } = await SB.auth.updateUser({password: pw});
  if (error) return alert("Couldn't set password: " + error.message);
  alert("Password set. Next time just enter your email and password.");
}
async function verifyCode(email){
  const token = ($("otp")?.value||"").trim(); if(!token) return;
  const { data, error } = await SB.auth.verifyOtp({email, token, type:"email"});
  if (error) return alert("That code didn't work: " + error.message);
  USER = data.user; dbLoad();
}
async function signOut(){ await SB.auth.signOut(); USER=null; WL.v=null; PT.v=null; try{localStorage.removeItem("watchlists");localStorage.removeItem("paper_trades");}catch(e){} DBSTATE="signedout"; render(); }
function accountBox(){
  if (DBSTATE==="off") return `<div class="mute" style="margin-top:8px;font-size:12px">Database not connected yet — saved on this device for now, and moved to your account automatically once sign-in is set up.</div>`;
  if (DBSTATE==="signedout") return `<div id="acct" style="margin-top:10px">${DBERR?`<div class="bad" style="font-size:13px;margin-bottom:6px">${esc(DBERR)}</div>`:""}
    <div class="mute">Sign in to save your lists and trades to your account (works on every device):</div>
    <input id="em" type="email" autocomplete="email" placeholder="your@email.com" style="width:100%;padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:16px;margin:6px 0">
    <input id="pw" type="password" autocomplete="current-password" placeholder="Password" style="width:100%;padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:16px;margin:6px 0">
    <div class="btnrow"><button class="sbtn pri" onclick="signInPw()">Sign in</button><button class="sbtn" onclick="signIn()">Email me a sign-in link instead</button></div>
    <div class="mute" style="margin-top:6px;font-size:12px">First time? Use the email link once, then tap “Set a password” — after that you can sign in with your password on any device.</div></div>`;
  if (DBSTATE==="loading") return `<div class="mute" style="margin-top:8px">Loading your account…</div>`;
  if (DBSTATE==="error") return `<div class="bad" style="margin-top:8px;font-size:13px">Database error: ${esc(DBERR)} <a href="#" onclick="dbLoad();return false" style="color:inherit">retry</a></div>`;
  return `<div class="mute" style="margin-top:8px;font-size:12px">☁ Saved to your account (${esc(USER.email)}) · <a href="#" onclick="setPassword();return false" style="color:var(--acc)">Set a password</a> · <a href="#" onclick="signOut();return false" style="color:var(--acc)">Sign out</a></div>`;
}
function modal(html){ const m=document.createElement("div"); m.className="modal"; m.innerHTML=`<div class="mbox">${html}</div>`; m.onclick=e=>{ if(e.target===m) m.remove(); }; document.body.appendChild(m); return m; }
function closeModal(){ document.querySelectorAll(".modal").forEach(m=>m.remove()); }

function addToList(t){
  const w = WL.get(); const names = Object.keys(w.lists);
  modal(`<h3 style="margin:0 0 8px">Add ${tk(t)} to a watchlist</h3>
    ${names.map(n=>`<button class="pill ${w.lists[n].includes(t)?"on":""}" style="margin:4px 4px 0 0" onclick="toggleInList('${t}', decodeURIComponent('${encodeURIComponent(n)}'))">${w.lists[n].includes(t)?"✓ ":""}${esc(n)} (${w.lists[n].length})</button>`).join("")}
    <div style="margin-top:12px" class="mute">Or create a new list:</div>
    <input id="nl" placeholder="e.g. Oil plays, Dividend ideas">
    <div class="btnrow"><button class="sbtn pri" onclick="const n=$('nl').value.trim(); if(n){ newList(n); toggleInList('${t}', n); }">Create &amp; add</button><button class="sbtn" onclick="closeModal()">Done</button></div>`);
}
function toggleInList(t, n){ const w=WL.get(); const a=w.lists[n]||(w.lists[n]=[]); const i=a.indexOf(t); i>=0?a.splice(i,1):a.push(t); WL.save(); dbList(n); closeModal(); addToList(t); }
function newList(n){ const w=WL.get(); if(!w.lists[n]) w.lists[n]=[]; w.cur=n; WL.save(); dbList(n); }
function renameList(){ const w=WL.get(), old=w.cur; const n=(prompt("Rename list", old)||"").trim(); if(!n||n===old||w.lists[n]) return; w.lists[n]=w.lists[old]; delete w.lists[old]; w.cur=n; WL.save(); dbList(n); dbListDel(old); render(); }
function deleteList(){ if(!confirm("Delete this list?")) return; const w=WL.get(), old=w.cur; delete w.lists[old]; if(!Object.keys(w.lists).length) w.lists["My watchlist"]=[]; w.cur=Object.keys(w.lists)[0]; WL.save(); dbListDel(old); render(); }
function removeFromList(t){ const w=WL.get(); w.lists[w.cur]=w.lists[w.cur].filter(x=>x!==t); WL.save(); dbList(w.cur); render(); }

function paperBuy(t){
  const r = ALL[t]; if(!r) return alert("No current price for this stock.");
  const cur = CUR(r.market)+" ";
  modal(`<h3 style="margin:0 0 4px">Paper buy ${tk(t)}</h3><div class="mute">Pretend purchase at the latest close: <b>${cur}${r.price}</b>. Label today: ${badge(r.signal||"HOLD")} score ${r.score}.</div>
    <label class="mute" style="display:block;margin-top:10px">Amount to invest (${CUR(r.market)})</label><input id="amt" inputmode="decimal" value="${r.market==="PSX"?100000:1000}">
    <label class="mute">Note (optional)</label><input id="nt" placeholder="Why I'm buying">
    <div class="btnrow"><button class="sbtn pri" onclick="doPaperBuy('${t}')">Buy (paper)</button><button class="sbtn" onclick="closeModal()">Cancel</button></div>`);
}
function doPaperBuy(t){
  const r = ALL[t], amt = Number($("amt").value)||0; if(amt<=0) return;
  const s = D.stats[r.market]||{};
  const trade = {id:Date.now(), ticker:t, market:r.market, date:s.price_date||D.generated.slice(0,10), price:r.price, idx:s.index_level,
    label:r.signal||"HOLD", hz:r.hz||["","",""], flags:r.flags||[], score:r.score, currency:CUR(r.market), amount:amt, shares:amt/r.price, note:$("nt").value.trim(), status:"open"};
  PT.get().unshift(trade); PT.save(); dbTrade(trade); closeModal(); alert(`Paper bought ${tk(t)}. See the Paper tab.`);
}
function paperSell(id){
  const x = PT.get().find(z=>z.id===id), r = ALL[x.ticker], s = D.stats[x.market]||{};
  if(!r) return alert("No current price — can't close today.");
  if(!confirm(`Close ${tk(x.ticker)} at ${r.price}?`)) return;
  Object.assign(x, {status:"closed", exit_price:r.price, exit_date:s.price_date, exit_idx:s.index_level, exit_label:r.signal||"HOLD"}); PT.save(); dbTrade(x); render();
}
function paperDel(id){ if(!confirm("Delete this paper trade?")) return; PT.v = PT.get().filter(z=>z.id!==id); PT.save(); dbTradeDel(id); render(); }
function tradeStats(x){
  const r = ALL[x.ticker], s = D.stats[x.market]||{};
  const px = x.status==="closed" ? x.exit_price : r?.price, ix = x.status==="closed" ? x.exit_idx : s.index_level;
  const ret = px && x.price ? px/x.price-1 : null, iret = ix && x.idx ? ix/x.idx-1 : null;
  const days = Math.max(0, Math.round((new Date((x.status==="closed"?x.exit_date:s.price_date)||Date.now()) - new Date(x.date))/864e5));
  return {px, ret, vs: ret!=null&&iret!=null ? ret-iret : null, iret, days, now: r};
}
function exportData(){
  const blob = new Blob([JSON.stringify({watchlists:WL.get(), paper:PT.get()}, null, 1)], {type:"application/json"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "screener-backup.json"; a.click();
}
function importData(){
  modal(`<h3 style="margin:0 0 6px">Restore backup</h3><div class="mute">Choose a screener-backup.json file. This replaces the lists and trades on this device.</div>
    <input type="file" id="imf" accept=".json,application/json"><div class="btnrow"><button class="sbtn pri" onclick="doImport()">Restore</button><button class="sbtn" onclick="closeModal()">Cancel</button></div>`);
}
function doImport(){ const f=$("imf").files[0]; if(!f) return; f.text().then(txt=>{ try{ const j=JSON.parse(txt); if(j.watchlists){WL.v=j.watchlists;WL.save(); Object.keys(WL.v.lists).forEach(dbList);} if(j.paper){PT.v=j.paper;PT.save(); PT.v.forEach(dbTrade);} closeModal(); render(); }catch(e){ alert("That file isn't a valid backup."); } }); }

function renderMine(){
  const F = getF(), q = $("q").value.trim().toLowerCase();
  const backup = accountBox() + `<div class="mute" style="margin-top:4px;font-size:12px"><a href="#" onclick="exportData();return false" style="color:var(--acc)">Export</a> · <a href="#" onclick="importData();return false" style="color:var(--acc)">Import</a></div>`;
  let rows = rowsFor(M);
  if (q) rows = rows.filter(r=>r.ticker.toLowerCase().startsWith(q) || (r.name||"").toLowerCase().includes(q));
  const active = activeCount(F);
  const key = SORTS[F.sort] ? F.sort : "score";
  $("fbtn").textContent = active ? `Filters (${active})` : "Filters"; $("fbtn").classList.toggle("on", !!active);
  $("freset").style.display = active ? "block" : "none"; $("sortbtn").textContent = "Sort: " + SORTS[key].l;
  $("more").style.display = "none";
  if ($("fpanel").classList.contains("open")) drawPanel();
  if (M==="Lists" && getF().req){ return renderRequested(backup); }
  if (M==="Lists"){
    const w = WL.get(), names = Object.keys(w.lists);
    if (!w.lists[w.cur]) w.cur = names[0];
    $("mine").innerHTML = `<div class="mine-head"><b>Watchlists</b><div class="pills" style="margin-top:8px"><button class="pill" onclick="getF().req=1;saveF();render()">⊕ Requested${TRACKED?` (${TRACKED.length})`:""}</button>${names.map(n=>`<button class="pill ${n===w.cur?"on":""}" onclick="WL.get().cur=decodeURIComponent('${encodeURIComponent(n)}');WL.save();render()">${esc(n)} (${w.lists[n].length})</button>`).join("")}</div>
      <div class="btnrow"><button class="sbtn" onclick="const n=prompt('New list name'); if(n&&n.trim()){ newList(n.trim()); render(); }">+ New list</button>
      ${w.cur?`<button class="sbtn" onclick="renameList()">Rename</button><button class="sbtn neg" onclick="deleteList()">Delete list</button>`:""}</div>
      <div class="mute" style="margin-top:8px">Add stocks from any market: open a stock and tap ☆ Watchlist.</div>${backup}</div>`;
    let shown = rows.filter(r=>passes(r,F)); if (key!=="score") shown.sort((a,b)=>SORTS[key].f(a,b)); else shown.sort((a,b)=>b.score-a.score);
    const missing = (w.lists[w.cur]||[]).filter(t=>!ALL[t]);
    $("count").textContent = `${shown.length} of ${(w.lists[w.cur]||[]).length} stocks${active?" match":""}`;
    $("list").innerHTML = shown.map((r,i)=>card(r,i,`<button class="cardx" onclick="event.stopPropagation(); removeFromList('${r.ticker}')" title="Remove">✕</button>`)).join("")
      + (missing.length?`<div class="box mute">Not in today's data: ${missing.map(tk).join(", ")}</div>`:"")
      + (!(w.lists[w.cur]||[]).length?`<div class="box mute">This list is empty. Open any stock and tap ☆ Watchlist.</div>`:"");
    return;
  }
  // Paper trades
  const all = PT.get();
  const st = F.st || "all";
  let trades = all.filter(x=>{ const r = ALL[x.ticker]; if (st!=="all" && x.status!==st) return false;
    if (q && !(x.ticker.toLowerCase().startsWith(q) || (r?.name||"").toLowerCase().includes(q))) return false;
    if (!active) return true; return r ? passes(r,F) : !(F.mk||[]).length || F.mk.includes(x.market); });
  const S = trades.map(x=>({x, ...tradeStats(x)}));
  const done = S.filter(z=>z.ret!=null), wins = done.filter(z=>z.vs>0).length;
  const avg = a => a.length ? a.reduce((p,c)=>p+c,0)/a.length : null;
  const byLab = {}; done.forEach(z=>{ const h=z.x.hz||[]; const k = h[0]==="BUY"?"SHORT BUY":h[2]==="BUY"&&z.x.label!=="BUY"?"LONG BUY":z.x.label==="BUY"?"MED BUY":z.x.label; (byLab[k] ||= []).push(z); });
  if (key!=="score") {} 
  S.sort((a,b)=> (b.x.id - a.x.id));
  $("mine").innerHTML = `<div class="mine-head"><b>Paper trades</b>
    <div class="pills" style="margin-top:8px">${[["all","All"],["open","Open"],["closed","Closed"]].map(([v,l])=>`<button class="pill ${st===v?"on":""}" onclick="getF().st='${v}';saveF();render()">${l} (${v==="all"?all.length:all.filter(x=>x.status===v).length})</button>`).join("")}</div>
    ${done.length?`<div class="grid" style="margin-top:10px">
      <div class="kv"><small>Average return</small><b class="${avg(done.map(z=>z.ret))>=0?"good":"bad"}">${fp(avg(done.map(z=>z.ret)))}</b></div>
      <div class="kv"><small>Average vs index</small><b class="${avg(done.map(z=>z.vs).filter(v=>v!=null))>=0?"good":"bad"}">${fp(avg(done.map(z=>z.vs).filter(v=>v!=null)))}</b></div>
      <div class="kv"><small>Beat the index</small><b>${wins} of ${done.length} (${Math.round(wins/done.length*100)}%)</b></div>
      <div class="kv"><small>Total P&amp;L</small><b>${(()=>{ const byCur={}; done.forEach(z=>{ const c=CUR(z.x.market)+" "; byCur[c]=(byCur[c]||0)+z.x.amount*z.ret; }); return Object.entries(byCur).map(([c,v])=>`${v>=0?"+":"−"}${c}${Math.abs(v).toFixed(0)}`).join(" · "); })()}</b></div></div>
      <div class="mute" style="margin-top:8px">By label when bought: ${Object.entries(byLab).map(([l,a])=>`${l} ${fp(avg(a.map(z=>z.vs).filter(v=>v!=null)))} vs index (${a.length})`).join(" · ")}</div>`:`<div class="mute" style="margin-top:8px">No paper trades yet. Open a stock and tap “Paper buy” to test a signal.</div>`}
    ${backup}</div>`;
  $("count").textContent = active||q ? `${trades.length} of ${all.length} trades match` : "";
  const cur = m => CUR(m)+" ";
  $("list").innerHTML = S.map(({x,px,ret,vs,iret,days,now})=>`<div class="trade">
    <div class="row"><div><span class="tk" onclick="openStock('${x.ticker}')" style="cursor:pointer">${tk(x.ticker)}</span> <span class="mute">${x.market}</span> ${x.status==="closed"?'<span class="sig HOLD">CLOSED</span>':""}</div>
      <div class="big2 ${ret>=0?"good":"bad"}">${fp(ret)}</div></div>
    <div class="mute">${esc(now?.name||"")}</div>
    <div style="font-size:13px;margin-top:6px">Bought ${x.date} at ${cur(x.market)}${x.price} as ${badge(x.label==="SELL"?"AVOID":x.label==="HOLD"?"":(x.hz||[]).includes("BUY")?"BUY":x.label)} ${subTags({hz:x.hz})} (score ${x.score}) · ${x.status==="closed"?`sold ${x.exit_date} at ${cur(x.market)}${x.exit_price}`:`now ${cur(x.market)}${px??"–"} ${now?badge(mainLabel(now)):""}`}</div>
    <div style="font-size:13px;margin-top:4px">Index ${fp(iret)} over the same ${days} days → <b class="${vs>=0?"good":"bad"}">${fp(vs)} vs index</b> · ${cur(x.market)}${x.amount} invested → ${ret!=null?`${ret>=0?"+":"−"}${cur(x.market)}${Math.abs(x.amount*ret).toFixed(0)}`:"–"}</div>
    ${x.note?`<div class="mute" style="margin-top:4px">“${esc(x.note)}”</div>`:""}
    <div class="btnrow">${x.status==="open"?`<button class="sbtn" onclick="paperSell(${x.id})">Close (sell)</button>`:""}<button class="sbtn" onclick="openStock('${x.ticker}')">Details</button><button class="sbtn neg" onclick="paperDel(${x.id})">Delete</button></div></div>`).join("");
}

/* ---------------- requested (on-demand) stocks ---------------- */
let TRACKED = null;
async function loadTracked(){
  if (DBSTATE!=="ready") { TRACKED = []; return; }
  const { data, error } = await SB.from("tracked_stocks").select("ticker,market,created_at").order("created_at",{ascending:false});
  TRACKED = error ? [] : data; render();
}
async function untrack(t){
  if (!confirm(`Stop tracking ${tk(t)}? It will no longer be analysed each day.`)) return;
  await SB.from("tracked_stocks").delete().eq("ticker", t); TRACKED = null; render();
}
function renderRequested(backup){
  if (TRACKED===null) { loadTracked(); }
  const items = TRACKED||[];
  $("count").textContent = ""; $("more").style.display = "none";
  $("mine").innerHTML = `<div class="mine-head"><b>Requested stocks</b> <a href="#" onclick="getF().req=0;saveF();render();return false" style="color:var(--acc);font-size:13px">‹ back to watchlists</a>
    <div class="mute" style="margin-top:6px">Stocks outside the screener that you asked to analyse. They're included in every daily run. To add one, search its ticker in a market tab and tap “Analyse”.</div>${backup}</div>`;
  if (DBSTATE!=="ready") { $("list").innerHTML = `<div class="box mute">Sign in above to request and see on-demand stocks.</div>`; return; }
  if (!items.length) { $("list").innerHTML = `<div class="box mute">None yet.</div>`; return; }
  $("list").innerHTML = items.map(x=>{
    const r = ALL[x.ticker], st = (EXTRAS.items||{})[x.ticker];
    if (r) return card(r, 0, `<button class="cardx" onclick="event.stopPropagation(); untrack('${x.ticker}')" title="Stop tracking">✕</button>`);
    const msg = st && st.status==="not_found" ? `<span class="bad">Not found on Yahoo Finance as a ${x.market} stock</span>`
      : st && st.status==="waiting" ? "Queued for the next daily run" : `Analysing… usually ready ~15–20 min after the request`;
    return `<div class="card"><button class="cardx" onclick="untrack('${x.ticker}')" title="Remove">✕</button><span class="tk">${tk(x.ticker)}</span> <span class="mute">${x.market}</span><div class="mute" style="margin-top:4px">${msg}</div></div>`;
  }).join("");
  if (items.some(x=>!ALL[x.ticker] && !((EXTRAS.items||{})[x.ticker]||{}).status)) pollExtras();
}

/* ---------------- run log ---------------- */
let LOG = null;
fetch("runlog.json").then(r=>r.ok?r.json():[]).then(j=>{ LOG=j; renderLog(); }).catch(()=>{ LOG=[]; });
function renderLog(){
  if (!LOG) return;
  if (!LOG.length){ $("logsum").textContent=""; $("runlog").innerHTML='<div class="mute">No runs logged yet.</div>'; return; }
  const l0 = LOG[0];
  $("logsum").innerHTML = `· last run <b class="st-${l0.status}">${l0.status.toUpperCase()}</b>`;
  const when = iso => new Date(iso).toLocaleString(undefined,{weekday:"short",day:"numeric",month:"short",hour:"numeric",minute:"2-digit"});
  const ic = st => st==="OK"?'<b class="st-ok">✓</b>':st==="INFO"?'<b class="mute">ℹ</b>':st==="WARN"?'<b class="st-warnings">⚠</b>':'<b class="st-failed">✗</b>';
  $("runlog").innerHTML = LOG.slice(0,12).map((l,i)=>`<details class="logrow" ${i===0?"open":""}><summary><b class="st-${l.status}">${l.status.toUpperCase()}</b> · ${when(l.started)} · ${l.minutes} min · ${l.trigger==="schedule"?"scheduled":"manual"}${l.commit?` · ${l.commit}`:""}</summary>
    ${l.fatal?`<div class="bad" style="margin-top:6px">Run crashed: ${esc(l.fatal)}</div>`:""}
    ${Object.entries(l.markets||{}).map(([m,v])=>`<div style="margin-top:8px"><b>${m}</b> ${v.error?`<span class="bad">failed — ${esc(v.error)}</span>`:`<span class="mute">${v.screened}/${v.downloaded} stocks · prices to ${v.price_date||"–"} · AI ${v.ai_scoring}</span>`}
      ${((l.checks||{})[m]||[]).map(c=>`<div class="chk" style="font-size:12.5px;padding:3px 0">${ic(c.status)}<span><b>${esc(c.stage)}</b>: ${esc(c.msg)}${c.hint?`<div class="mute">→ ${esc(c.hint)}</div>`:""}</span></div>`).join("")}
      ${v.timings?`<div class="mute" style="font-size:12px">Time: ${Object.entries(v.timings).map(([k,t])=>`${k} ${t}s`).join(" · ")}</div>`:""}
      ${(v.missing_prices||[]).length?`<div class="mute" style="font-size:12px">No prices: ${v.missing_prices.map(tk).join(", ")}</div>`:""}
      ${Object.entries((l.errors||{})[m]||{}).map(([k,arr])=>`<details><summary class="mute" style="font-size:12px">${esc(k)} (${arr.length})</summary><div class="mute" style="font-size:11.5px;white-space:pre-wrap">${arr.map(esc).join("\n")}</div></details>`).join("")}
    </div>`).join("")}
    ${(l.warnings||[]).length?`<details><summary class="mute" style="font-size:12px">All warnings (${l.warnings.length})</summary><div class="mute" style="font-size:11.5px;white-space:pre-wrap">${l.warnings.map(esc).join("\n")}</div></details>`:""}
  </details>`).join("")
    + `<div class="mute" style="margin-top:6px;font-size:12px">Full text logs: repo → results/logs. ✓ ok · ⚠ warning · ✗ failed. Each warning says where to look.</div>`;
}

/* ---------------- market overview ---------------- */
const PER = ["1D","1W","1M","3M","YTD","1Y","5Y"];
const fp = v => v==null ? "–" : (v>0?"+":"") + (v*100).toFixed(Math.abs(v)<0.1?1:0) + "%";
function heatBg(v, lab){ if(v==null) return "transparent"; const scale = {"1D":0.03,"1W":0.06,"1M":0.12,"3M":0.2,"YTD":0.3,"1Y":0.4,"5Y":1}[lab]||0.2;
  const a = Math.min(1, Math.abs(v)/scale)*0.55+0.08; return v>=0 ? `rgba(70,160,110,${a})` : `rgba(200,90,70,${a})`; }
function renderOverview(s){
  const p = s.perf; if(!p){ $("ov").innerHTML = '<div class="mute">Not available yet — appears after the next run.</div>'; $("ovsum").textContent=""; return; }
  const idxName = {US:"S&P 500 (SPY)", ASX:"ASX 200", PSX:"KSE-100 (built from members)",
    COM:"Commodities basket (equal weight)", CRYPTO:"Top-50 crypto basket (equal weight)"}[M] || "Index";
  $("ovsum").innerHTML = `· today <b style="color:${(p.index["1D"]||0)>=0?"var(--acc)":"var(--neg)"}">${fp(p.index["1D"])}</b> · 1Y ${fp(p.index["1Y"])}`;
  const sec = p.sectors, ind = p.industries;
  const best = ind.slice(0,5), worst = ind.slice(-5).reverse();
  $("ov").innerHTML = `<div class="mute">${idxName} · returns in ${CUR(M)}</div>
    <div class="perf">${PER.map(k=>`<div style="background:${heatBg(p.index[k],k)}"><small>${k}</small><b>${fp(p.index[k])}</b></div>`).join("")}</div>
    <div class="mute" style="margin:4px 0">${M==="COM"?"Groups (equal weight)":M==="CRYPTO"?"Groups (weighted by market cap)":"Sectors (weighted by company size)"} — tap one to filter:</div>
    <div class="heatwrap"><table class="heat"><tr><th></th>${PER.map(k=>`<th>${k}</th>`).join("")}</tr>
    ${sec.map(r=>`<tr><td onclick="sectorFilter('${esc(r.name).replace(/'/g,"\\'")}')"><b style="font-weight:600">${esc(r.name)}</b> <span class="mute">${r.n}</span></td>${PER.map(k=>`<td style="background:${heatBg(r.ret[k],k)}">${fp(r.ret[k])}</td>`).join("")}</tr>`).join("")}</table></div>
    <div class="mute" style="font-size:11px;margin-top:2px">Swipe the table sideways for 1Y and 5Y.</div>
    ${ind.length?`<div style="margin-top:10px"><div><div class="mute" style="margin-bottom:4px">Best industries (1M)</div>${best.map(r=>`<div style="font-size:13px;display:flex;justify-content:space-between;gap:6px"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.name)}</span><b class="good">${fp(r.ret["1M"])}</b></div>`).join("")}</div>
      <div style="margin-top:10px"><div class="mute" style="margin-bottom:4px">Worst industries (1M)</div>${worst.map(r=>`<div style="font-size:13px;display:flex;justify-content:space-between;gap:6px"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.name)}</span><b class="bad">${fp(r.ret["1M"])}</b></div>`).join("")}</div></div>`:""}
    ${why(xOverviewMarket(p, idxName))}`;
}
function xOverviewMarket(p, idxName){
  const s = p.sectors.filter(r=>r.ret["1M"]!=null), lead = s[0], lag = s[s.length-1];
  const y = p.index["1Y"], t = p.index["1D"];
  const buyHeavy = [...p.sectors].sort((a,b)=>(b.labels.BUY+b.labels.WATCH)-(a.labels.BUY+a.labels.WATCH))[0];
  return `<p>The ${idxName} moved <b>${fp(t)}</b> on the last trading day and is <b>${fp(y)}</b> over the past year${p.index["5Y"]!=null?` (${fp(p.index["5Y"])} over five years)`:""}.</p>
    ${lead&&lag?`<p>Over the last month, <b>${esc(lead.name)}</b> led the market (${fp(lead.ret["1M"])}) and <b>${esc(lag.name)}</b> lagged (${fp(lag.ret["1M"])}).</p>`:""}
    ${buyHeavy&&(buyHeavy.labels.BUY+buyHeavy.labels.WATCH)>0?`<p>The sector with the most BUY/WATCH labels right now is <b>${esc(buyHeavy.name)}</b> (${buyHeavy.labels.BUY} buy, ${buyHeavy.labels.WATCH} watch).</p>`:""}
    <p class="mute">Green = up, red = down; stronger colour = bigger move for that time frame. Sector returns are weighted by company size, like an index.</p>`;
}
function sectorFilter(sec){ resetF(); getF().sec=[sec]; saveF(); render(); window.scrollTo({top:$("count").offsetTop-60,behavior:"smooth"}); }

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
  dy:{l:"Dividend yield (highest first)", f:(a,b)=>(b.dy??-1)-(a.dy??-1)},
};
const DEF = () => ({hal:"", div:"", dymin:"", dymax:"", hz:[], mk:[], flg:[], sig:[], sec:[], smin:"", smax:"", parts:{}, pemin:"", pemax:"", rmin:"", rmax:"", rsimin:"", rsimax:"",
  cap:"", news:"", macro:"", good:[], bad:[], tags:[], sort:"score", vqmin:{}});
const FS = {};
function getF(){ if(!FS[M]){ try{ FS[M] = Object.assign(DEF(), JSON.parse(localStorage.getItem("f_"+M)||"{}")); }catch(e){ FS[M]=DEF(); } FS[M].sig = FS[M].sig||[]; } return FS[M]; }
function saveF(){ try{ localStorage.setItem("f_"+M, JSON.stringify(FS[M])); }catch(e){} }
const num = v => v===""||v==null ? null : Number(v);
function activeCount(F){ let n=0;
  if(F.sig.length) n++; if((F.flg||[]).length) n++; if((F.hz||[]).length) n++; if(F.hal) n++; if(F.div) n++; if(F.dymin!==""||F.dymax!=="") n++; if((F.mk||[]).length) n++; if(F.sec.length) n++; if(F.smin!==""||F.smax!=="") n++;
  n += Object.values(F.parts).filter(v=>v>0).length; n += Object.values(F.vqmin).filter(v=>v>0).length;
  if(F.pemin!==""||F.pemax!=="") n++; if(F.rmin!==""||F.rmax!=="") n++; if(F.rsimin!==""||F.rsimax!=="") n++;
  if(F.cap) n++; if(F.news) n++; if(F.macro) n++; n += F.good.length?1:0; n += F.bad.length?1:0; n += F.tags.length?1:0; return n; }
function passes(r, F){
  if ((F.mk||[]).length && !F.mk.includes(r.market)) return false;
  if (F.hal==="HALAL" && r.hl!=="HALAL") return false;
  if (F.hal==="OK" && !(r.hl==="HALAL"||r.hl==="DOUBTFUL")) return false;
  if (F.hal==="NOT HALAL" && r.hl!=="NOT HALAL") return false;
  const dv = r.dv||[];
  if (F.div==="pays" && !(r.dy>0)) return false;
  if (F.div==="div" && !(dv.includes("Dividend")||dv.includes("High dividend"))) return false;
  if (F.div==="high" && !dv.includes("High dividend")) return false;
  if (F.div==="grow" && !dv.includes("Dividend grower")) return false;
  if (F.div==="safe" && !((dv.includes("Dividend")||dv.includes("High dividend")) && !dv.includes("Dividend at risk"))) return false;
  if (F.div==="none" && r.dy>0) return false;
  if (num(F.dymin)!=null && !(r.dy!=null && r.dy >= num(F.dymin))) return false;
  if (num(F.dymax)!=null && !(r.dy!=null && r.dy <= num(F.dymax))) return false;
  if (F.sig.length){ const sg = mainLabel(r)||"NONE"; if(!F.sig.includes(sg)) return false; }
  if ((F.flg||[]).length && !F.flg.some(f=>(r.flags||[]).includes(f))) return false;
  if ((F.hz||[]).length){ const h = r.hz||["","",""]; const ok = {S:h[0]==="BUY", M:h[1]==="BUY", L:h[2]==="BUY", SW:h[0]==="WATCH", LW:h[2]==="WATCH"};
    if (!F.hz.some(k=>ok[k])) return false; }
  if (F.sec.length && !F.sec.includes(r.sector)) return false;
  if (num(F.smin)!=null && r.score < num(F.smin)) return false;
  if (num(F.smax)!=null && r.score > num(F.smax)) return false;
  for (const [k,v] of Object.entries(F.parts)) if (v>0 && (r.parts[k]??0) < v) return false;
  const vq = {value:r.vq?.[0], quality:r.vq?.[1], growth:r.vq?.[2], health:r.vq?.[3]};
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
  const F = getF(), rows = rowsFor(M);
  const secs = [...new Set(rows.map(r=>r.sector).filter(Boolean))].sort();
  const evs = [...new Set(rows.flatMap(r=>r.events||[]))];
  const good = evs.filter(e=>!BAD.includes(e)).sort(), bad = evs.filter(e=>BAD.includes(e)).sort();
  const tags = [...new Set(rows.flatMap(r=>r.reasons||[]))].filter(t=>!evs.includes(t)).sort();
  const A = ASSET(M) && !MINE(M);
  const caps = M==="CRYPTO" ? [["",'Any'],["1e11",">USD 100B"],["1e10",">USD 10B"],["-5e9","<USD 5B"]] : M==="US" ? [["",'Any'],["1e10",">USD 10B"],["5e10",">USD 50B"],["2e11",">USD 200B"],["-2e10","<USD 20B"]]
             : M==="ASX" ? [["",'Any'],["2e9",">AUD 2B"],["1e10",">AUD 10B"],["5e10",">AUD 50B"],["-5e9","<AUD 5B"]]
             : [["",'Any'],["5e10",">PKR 50B"],["2e11",">PKR 200B"],["5e11",">PKR 500B"],["-5e10","<PKR 50B"]];
  $("fpanel").innerHTML = `
   ${MINE(M)?`<div class="fg"><span class="fl">Market</span>${pills("mk",MARKETS.map(m=>[m,MNAME(m)]),F.mk||[])}</div>`:""}
   <div class="fg"><span class="fl">Signal</span>${pills("sig",[["BUY","BUY"],["WATCH","WATCH"],["AVOID","AVOID"],["NONE","No label"],["HOLD","HOLD (in Paper)"],["SELL","SELL (in Paper)"]],F.sig)}
     <div class="mute" style="margin-top:4px">Tap several to combine, e.g. BUY + WATCH.</div></div>
   <div class="fg"><span class="fl">Time horizon</span>${pills("hz",[["S","Short-term BUY"],["M","Medium-term BUY"],["L","Long-term BUY"],["SW","Short WATCH"],["LW","Long WATCH"]],F.hz||[])}</div>
   <div class="fg"><span class="fl">Shariah (halal)</span>${one("hal",[["","Any"],["HALAL","Halal only"],["OK","Halal + doubtful"],["NOT HALAL","Not halal"]],F.hal||"")}</div>
   ${A?"":`<div class="fg"><span class="fl">Dividends</span>${one("div",[["","Any"],["pays","Pays a dividend"],["div","Dividend stock"],["high","High dividend"],["grow","Dividend grower"],["safe","Dividend, not at risk"],["none","No dividend"]],F.div||"")}
     <div style="margin-top:6px">${rng("dymin","dymax","min yield % e.g. 3","max")}</div>
     <div class="mute" style="margin-top:4px">Dividend stock = yield 2%+ and paid every year for 3+ years. High = top fifth of this market's payers (at least 4%). Grower = raised it 5+ years in a row.</div></div>`}
   <div class="fg"><span class="fl">Flags</span>${pills("flg",[["REBOUND","REBOUND (oversold quality)"],["TAKE PROFIT","TAKE PROFIT"]],F.flg)}</div>
   <div class="fg"><span class="fl">${A?"Group":"Sector"}</span>${pills("sec",secs.map(x=>[x,x]),F.sec)}</div>
   <div class="fg"><span class="fl">Overall score</span>${rng("smin","smax","min e.g. 60","max")}</div>
   <div class="fg"><span class="fl">Minimum part scores (0–100 rank)</span>
     ${PARTS.filter(([k])=>!(A&&k==="fundamental")).map(([k,l])=>`<div class="sl"><span>${A?({news:"News",peers:"Group news",macro:"Macro & politics"}[k]||l):l}</span><input type="range" min="0" max="95" step="5" value="${F.parts[k]||0}" oninput="this.nextElementSibling.textContent=this.value" onchange="F_part('${k}',this.value)"><b>${F.parts[k]||0}</b></div>`).join("")}
     ${(A?[]:[["value","Value vs sector"],["quality","Quality"],["growth","Growth"],["health","Financial health"]]).map(([k,l])=>`<div class="sl"><span>${l}</span><input type="range" min="0" max="95" step="5" value="${F.vqmin[k]||0}" oninput="this.nextElementSibling.textContent=this.value" onchange="F_vq('${k}',this.value)"><b>${F.vqmin[k]||0}</b></div>`).join("")}</div>
   <div class="fg"><span class="fl">${A?"News":"Company news"}</span>${one("news",[["","Any"],["pos","Positive"],["notneg","Not negative"],["neg","Negative"],["has","Has news"]],F.news)}</div>
   <div class="fg"><span class="fl">Sector & politics</span>${one("macro",[["","Any"],["tail","Tailwind"],["nohead","No headwind"],["head","Headwind"]],F.macro)}</div>
   ${good.length?`<div class="fg"><span class="fl">Has a recent event (any of)</span>${pills("good",good.map(x=>[x,x]),F.good)}</div>`:""}
   ${bad.length?`<div class="fg"><span class="fl">Exclude stocks with</span>${pills("bad",bad.map(x=>[x,x]),F.bad,true)}</div>`:""}
   ${A?"":`<div class="fg"><span class="fl">P/E</span>${rng("pemin","pemax","min","max e.g. 20")}</div>`}
   <div class="fg"><span class="fl">3-month return %</span>${rng("rmin","rmax","min e.g. 0","max")}</div>
   <div class="fg"><span class="fl">RSI (14 day)</span>${rng("rsimin","rsimax","min","max e.g. 70")}<div class="mute" style="margin-top:4px">Under 30 = oversold, over 70 = overbought.</div></div>
   ${MINE(M)||M==="COM"?"":`<div class="fg"><span class="fl">Market cap</span>${one("cap",caps,F.cap)}</div>`}
   ${tags.length?`<div class="fg"><span class="fl">Must have all of these tags</span>${pills("tags",tags.map(x=>[x,x]),F.tags)}</div>`:""}
   <div class="fg"><label>Sort by</label><select onchange="setF('sort',this.value)">${Object.entries(SORTS).filter(([k])=>!(A&&["fundamental","pe_lo","dy"].includes(k))&&!(M==="COM"&&k==="mcap")).map(([k,v])=>`<option value="${k}" ${F.sort===k?"selected":""}>${v.l}</option>`).join("")}</select></div>
   <div class="fact"><button onclick="resetF()">Clear all</button><button class="pri" onclick="$('fpanel').classList.remove('open');window.scrollTo({top:$('count').offsetTop-60,behavior:'smooth'})">Show ${rowsFor(M).filter(r=>passes(r,F)).length} ${MINE(M)?"":NOUN(M)}</button></div>`;
}
function tog(g,v){ const F=getF(); const a=F[g]; const i=a.indexOf(v); i>=0?a.splice(i,1):a.push(v); saveF(); render(); }
function setF(k,v){ const F=getF(); F[k]=v; saveF(); render(); }
function F_part(k,v){ getF().parts[k]=Number(v); saveF(); render(); }
function F_vq(k,v){ getF().vqmin[k]=Number(v); saveF(); render(); }
function quickSig(sg){ resetF(); getF().sig=[sg]; saveF(); render(); window.scrollTo({top:$("count").offsetTop-60,behavior:"smooth"}); }
function resetF(){ FS[M]=DEF(); saveF(); render(); }
$("fbtn").onclick = ()=>{ $("fpanel").classList.toggle("open"); render(); };
$("freset").onclick = resetF;
$("sortbtn").onclick = ()=>{ const ks=Object.keys(SORTS), F=getF(); F.sort = ks[(ks.indexOf(F.sort)+1)%ks.length]; saveF(); render(); };

/* ---------------- market clock ---------------- */
const MK = {
  US:  {tz:"America/New_York", city:"New York", s:{1:[[570,960]],2:[[570,960]],3:[[570,960]],4:[[570,960]],5:[[570,960]]}},
  ASX: {tz:"Australia/Sydney", city:"Sydney", s:{1:[[600,960]],2:[[600,960]],3:[[600,960]],4:[[600,960]],5:[[600,960]]}},
  PSX: {tz:"Asia/Karachi", city:"Karachi", s:{1:[[570,930]],2:[[570,930]],3:[[570,930]],4:[[570,930]],5:[[555,720],[870,990]]}},
  /* CME futures: Sunday 6pm – Friday 5pm New York, with a daily break 5–6pm */
  COM: {tz:"America/New_York", city:"New York (CME)", s:{0:[[1080,1440]],1:[[0,1020],[1080,1440]],2:[[0,1020],[1080,1440]],3:[[0,1020],[1080,1440]],4:[[0,1020],[1080,1440]],5:[[0,1020]]}},
};
const WD = {Sun:0,Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6};
function tzParts(d, tz){ const p = {}; new Intl.DateTimeFormat("en-US",{timeZone:tz,weekday:"short",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(d).forEach(x=>p[x.type]=x.value); return {wd:WD[p.weekday], min:(+p.hour)*60+(+p.minute)}; }
function isOpen(m, d){ const t = tzParts(d, MK[m].tz); return (MK[m].s[t.wd]||[]).some(([a,b])=>t.min>=a && t.min<b); }
function fmtDur(ms){ const m = Math.round(ms/60000), d = Math.floor(m/1440), h = Math.floor((m%1440)/60), mm = m%60; return (d?d+"d ":"") + (d||h?h+"h ":"") + mm+"m"; }
function clockTick(){
  if (M==="CRYPTO"){ const c = new Date(); c.setUTCHours(24,0,0,0);
    $("clock").innerHTML = `<div><b>Crypto</b> · trades 24/7<div class="mute">Daily close at 00:00 UTC — next in ${fmtDur(c-new Date())} (${c.toLocaleString(undefined,{weekday:"short",hour:"numeric",minute:"2-digit"})} your time)</div></div><span class="st open">● OPEN</span>`; return; }
  const m = MK[M]; if(!m){ $("clock").innerHTML=""; return; }
  const now = new Date(), open = isOpen(M, now);
  let t = new Date(now); t.setSeconds(0,0);
  for (let i=0;i<60*24*8;i++){ t = new Date(t.getTime()+60000); if (isOpen(M,t)!==open) break; }
  const local = now.toLocaleTimeString("en-AU",{timeZone:m.tz,hour:"numeric",minute:"2-digit",weekday:"short"});
  const when = t.toLocaleString(undefined,{weekday:"short",hour:"numeric",minute:"2-digit"});
  $("clock").innerHTML = `<div><b>${MNAME(M)}</b> · ${m.city} ${local}<div class="mute">${open?"Closes":"Opens"} in ${fmtDur(t-now)} (${when} your time)</div></div><span class="st ${open?"open":"closed"}">${open?"● OPEN":"● CLOSED"}</span>`;
}
setInterval(clockTick, 30000);

$("more").onclick = ()=>{ showAll=!showAll; render(); };
$("q").oninput = render;
const MARKETS = Object.keys(D.markets);
/* Top tabs: Stocks (with US / ASX / PSX inside) | Commodities | Crypto | Lists | Paper */
const STOCKS = MARKETS.filter(m=>!ASSET(m));
let LASTSTOCK = STOCKS[0];
const TOP = m => STOCKS.includes(m) ? "Stocks" : m;
const go = m => { M=m; showAll=false; $("q").value=""; $("fpanel").classList.remove("open"); render(); };
[["Stocks","Stocks"], ...MARKETS.filter(ASSET).map(m=>[m, MNAME(m)]), ["Lists","Lists"], ["Paper","Paper"]].forEach(([k,l])=>{
  const b=document.createElement("button"); b.textContent=l; b.dataset.k=k;
  b.onclick=()=>go(k==="Stocks" ? LASTSTOCK : k); $("tabs").appendChild(b); });
STOCKS.forEach(m=>{ const b=document.createElement("button"); b.textContent=m; b.dataset.k=m; b.onclick=()=>go(m); $("subtabs").appendChild(b); });
const MINE = v => v==="Lists" || v==="Paper";
/* every stock from every market, keyed by ticker, with its market and rank */
const ALL = {};
MARKETS.forEach(m => (D.markets[m]||[]).forEach((r,i)=>{ ALL[r.ticker] = Object.assign({market:m, rank:i+1}, r); }));
/* ---- on-demand analysis results (extras.json, refreshed while something is pending) ---- */
let EXTRAS = {items:{}, rows:{}};
function mergeExtras(){
  Object.entries(EXTRAS.rows||{}).forEach(([t,r])=>{ if (!ALL[t] || ALL[t].extra) ALL[t] = Object.assign({extra:true}, r); });
}
async function loadExtras(){
  try { const r = await fetch("extras.json?t="+Date.now()); if (r.ok) { EXTRAS = await r.json(); mergeExtras(); render(); } } catch(e){}
}
function rowsFor(view){
  if (view==="Lists") return (WL.get().lists[WL.get().cur]||[]).map(t=>ALL[t]).filter(Boolean);
  if (view==="Paper") return [...new Set(PT.get().map(x=>x.ticker))].map(t=>ALL[t]).filter(Boolean);
  const base = (D.markets[view]||[]).map((r,i)=>Object.assign({market:view, rank:i+1}, r));
  const have = new Set(base.map(r=>r.ticker));
  const extra = Object.values(EXTRAS.rows||{}).filter(r=>r.market===view && !have.has(r.ticker)).map(r=>Object.assign({extra:true}, r));
  return base.concat(extra);
}

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
  sh.innerHTML = `<div class="shead"><button class="back" onclick="history.back()">‹ Back</button><b>${tk(d.ticker)}</b>${badge(mainLabel(dRow(d)))}</div>
  <div class="sec"><div class="hero"><div style="min-width:0"><div class="tk" style="font-size:20px">${esc(d.name)}</div>
    <div class="mute">${esc(d.sector)}${d.industry?" · "+esc(d.industry):""}</div>
    <div style="margin-top:8px">Price <b>${CUR(d.market)} ${d.price??"–"}</b>${d.mcap||!ASSET(d.market)?` · Market cap <b>${CUR(d.market)} ${fmtCap(d.mcap)}</b>`:""}</div>
    ${d.market==="COM"?`<div class="mute" style="margin-top:4px">${/=F$/.test(d.ticker)?"Front-month futures price (USD).":"Tracked through an ETF (USD)."}</div>`:""}</div>
    <div style="text-align:right"><div class="big">${d.score}</div><div class="mute">#${d.rank} of ${d.of}</div></div></div>
    <div class="chips" style="margin-top:8px">${subTags(dRow(d))}${d.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div>
    <div class="btnrow"><button class="sbtn" onclick="addToList('${d.ticker}')">☆ Watchlist</button><button class="sbtn pri" onclick="paperBuy('${d.ticker}')">Paper buy</button></div>
    ${why(xOverview(d), "In plain English")}</div>

  <div class="sec"><h3>Label: ${badge(mainLabel(dRow(d)))||'<span class="mute">none</span>'} <span class="mute" style="font-weight:400">${LABEL_INFO[mainLabel(dRow(d))]}</span></h3>
    ${(d.red_flags||[]).length?`<div style="margin-bottom:8px"><b style="color:var(--neg)">Red flags:</b> ${d.red_flags.map(esc).join(", ")}</div>`:""}
    <div class="fl" style="font-size:13px;font-weight:600;margin:4px 0">Buy checks (${d.checks.filter(c=>c.pass||c.skipped).length}/${d.checks.length})</div>
    ${d.checks.map(c=>`<div class="chk"><b class="${c.skipped?"skip":c.pass?"ok":"no"}">${c.skipped?"–":c.pass?"✓":"✗"}</b><span>${c.label}${c.skipped?' <span class="mute">(not used: model failed its test in this market)</span>':""}</span></div>`).join("")}
    ${d.sell_checks?`<div class="fl" style="font-size:13px;font-weight:600;margin:10px 0 4px">Sell warnings (${d.sell_checks.filter(c=>c.pass&&!c.skipped).length}/${d.sell_checks.filter(c=>!c.skipped).length})</div>
    ${d.sell_checks.map(c=>`<div class="chk"><b class="${c.skipped?"skip":c.pass?"no":"ok"}">${c.skipped?"–":c.pass?"!":"·"}</b><span>${c.label}</span></div>`).join("")}`:""}
    ${why(xLabel(d), "Why this label?")}</div>

  ${horizonSection(d)}

  ${historySection(d)}

  <div class="sec"><h3>Score breakdown</h3><div class="mute" style="margin-bottom:6px">Each part is a 0–100 rank vs the other ${ASSET(d.market)?NOUN(d.market):d.market+" stocks"}, weighted into the total.</div>
    ${d.parts.map(p=>`<div class="prow"><span>${p.label} <span class="mute">× ${Math.round(p.weight*100)}%</span></span><span class="v">${p.value}</span><i><span style="width:${p.value}%"></span></i></div>`).join("")}
    ${ASSET(d.market)?"":`<div class="grid" style="margin-top:10px"><div class="kv"><small>Value vs sector</small><b>${d.sub.value}</b></div><div class="kv"><small>Quality</small><b>${d.sub.quality}</b></div><div class="kv"><small>Growth</small><b>${d.sub.growth}</b></div><div class="kv"><small>Financial health</small><b>${d.sub.health??"–"}</b></div><div class="kv"><small>Analysts</small><b>${d.analyst.rating?esc(d.analyst.rating).replace("_"," "):"–"}</b></div></div>`}
    ${up!=null?`<div class="mute" style="margin-top:8px">Average analyst target ${CUR(d.market)} ${d.analyst.target} (${pct(up)} from here).</div>`:""}
    ${why(xScore(d, up))}</div>

  <div class="sec"><h3>Price chart</h3><div class="rng" id="rng"></div><div id="chart"></div><div id="tip"></div>
    <div class="legend"><span style="--c:var(--acc)">Price</span><span style="--c:var(--ma50)">50-day avg</span><span style="--c:var(--ma200)">200-day avg</span><span style="--c:var(--idx)">Index (scaled)</span></div>
    ${why(xChart(d, base))}</div>

  <div class="sec"><h3>Technicals</h3><div class="grid">${Object.entries(d.tech).map(([k,v])=>{
      const isPct = !/RSI|Volume/.test(k), s = v==null?"–": /Volatility/.test(k)? (v*100).toFixed(1)+"%" : isPct? pct(v) : (k.startsWith("Volume")? v.toFixed(2)+"x" : v);
      const cls = v==null?"": k.startsWith("RSI") ? (v>70?"bad":v<30?"good":"") : isPct && !/Volatility/.test(k) ? (v>0?"good":"bad") : "";
      return `<div class="kv"><small>${k}</small><b class="${cls}">${s}</b></div>`}).join("")}</div>
    ${why(xTech(d))}</div>

  ${ASSET(d.market)?"":`<div class="sec"><h3>Fundamentals vs sector</h3><table><tr><th>Metric</th><th>${tk(d.ticker)}</th><th>Sector median</th></tr>
    ${d.fund.map(f=>{ let cls=""; if(f.value!=null&&f.sector!=null){ const better = f.better==="high" ? f.value>f.sector : f.value<f.sector; cls = better?"good":"bad"; }
      return `<tr><td>${f.label}</td><td class="${cls}">${fmtF(f.value,f.kind)}</td><td>${fmtF(f.sector,f.kind)}</td></tr>`}).join("")}</table>
    <div class="mute" style="margin-top:6px">Green = better than the typical company in its sector.</div>
    ${why(xFund(d))}</div>`}

  ${ASSET(d.market)?"":healthSection(d)}

  ${ASSET(d.market)?"":dividendSection(d)}

  ${halalSection(d)}

  <div class="sec"><h3>News (last 10 days)</h3>
    ${d.events&&d.events.length?`<div class="chips" style="margin:0 0 8px">${d.events.map(e=>`<span class="chip ${e.impact<0?"bad":""}">${e.impact>0?"▲":e.impact<0?"▼":"•"} ${esc(e.label)}</span>`).join("")}</div>`:""}
    <div class="mute" style="margin-bottom:6px">Recency-weighted sentiment: <b style="color:${sentColor(d.news_avg)}">${d.news_avg??0}</b> · competitors: <b style="color:${sentColor(d.peer_avg)}">${d.peer_avg??0}</b>${d.macro_share>0?` · ${Math.round(d.macro_share*100)}% about policy/macro`:""}</div>
    ${d.news.length ? d.news.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}
      <div class="mute">${esc(n.publisher||"")}${n.quality==="promo"?" (promotional, half weight)":""} ${n.date||""}${n.macro?" · policy/macro":""}${(n.events||[]).map(e=>` · <b style="color:${BAD.includes(e)?"var(--neg)":"var(--acc)"}">${esc(e)}</b>`).join("")}</div></div>`).join("") : `<div class="mute">No recent headlines.</div>`}
    ${why(xNews(d))}</div>

  <div class="sec"><h3>${ASSET(d.market)?"Macro &amp; politics":"Sector &amp; politics"}</h3>
    <div class="grid"><div class="kv"><small>Macro score (−1 to 1)</small><b class="${d.macro.score>0.05?"good":d.macro.score<-0.05?"bad":""}">${d.macro.score>0?"+":""}${d.macro.score}</b></div>
    <div class="kv"><small>${esc(d.sector)} news mood</small><b class="${d.macro.sector_news>0.05?"good":d.macro.sector_news<-0.05?"bad":""}">${d.macro.sector_news>0?"+":""}${d.macro.sector_news}</b></div></div>
    ${d.macro.sector_why?`<div class="mute" style="margin-top:8px">${esc(d.macro.sector_why)}</div>`:""}
    ${d.macro.effects.length?`<div style="margin-top:10px;font-size:14px">${d.macro.effects.map(e=>`<div class="chk"><b class="${e.effect>0?"ok":"no"}">${e.effect>0?"▲":"▼"}</b><span>${esc(e.theme)} <span class="mute">(${e.effect>0?"+":""}${e.effect})</span></span></div>`).join("")}</div>`:`<div class="mute" style="margin-top:8px">No political or macro theme is notably affecting this stock right now.</div>`}
    ${d.macro.sector_headlines.length?`<div class="mute" style="margin:8px 0 2px">Sector headlines:</div>`+d.macro.sector_headlines.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}<div class="mute">${esc(n.publisher||"")} ${n.date||""}</div></div>`).join(""):""}
    ${why(xMacro(d))}</div>

  <div class="sec"><h3>${ASSET(d.market)?"Others in":"Peers in"} ${esc(d.sector)}</h3>
    ${d.peers.length ? d.peers.map(p=>`<div class="peer" onclick="openStock('${p.ticker}')"><span><b>${tk(p.ticker)}</b>${p.signal?`<span class="sig ${p.signal}">${p.signal}</span>`:""}<div class="mute">${esc(p.name)}</div></span>
      <span style="text-align:right"><b>${p.score}</b><div class="mute">3m ${pct(p.ret3m,0)}${ASSET(d.market)?"":` · P/E ${p.pe??"–"}`} · news <span style="color:${sentColor(p.news)}">${p.news??0}</span></div></span></div>`).join("") : `<div class="mute">No peers in the screened list.</div>`}
    ${why(xPeers(d))}</div>
  <footer>Not financial advice. Data from Yahoo Finance; may be delayed or incomplete.</footer>`;
  drawChart(d, base, 252);
}

/* the list-row shape of a stock, for label logic on the detail page */
function dRow(d){ return ALL[d.ticker] || {ticker:d.ticker, signal:d.signal, hz:[d.hz?.short||"", d.hz?.medium||"", d.hz?.long||""], hl:d.halal?.status, flags:d.flags}; }
function historySection(d){
  const h = d.label_history||[];
  const now = d.weakening ? `<div class="chk"><b class="no">!</b><span>Failed its checks today for the first time. The label stays until tomorrow's run — it only changes if it fails again.</span></div>` : "";
  if (!h.length && !now) return "";
  const when = w => { const x = new Date(w.replace(" ","T")+"Z"); return isNaN(x) ? w : x.toLocaleString(undefined,{day:"numeric",month:"short",hour:"numeric",minute:"2-digit"}); };
  return `<div class="sec"><h3>Label history</h3>${now}
    ${h.map(x=>`<div class="chk" style="font-size:13px"><b class="${["AVOID","SELL"].includes(x.to)?"no":x.to==="BUY"?"ok":"skip"}">•</b><span><b>${esc(x.field)}</b>: ${esc(x.from)} → <b>${esc(x.to)}</b> <span class="mute">· ${when(x.when)} · ${esc(x.why)}</span></span></div>`).join("")}
    ${why(`<p>Labels have memory so they don't flip on noise. Upgrades and real company red flags take effect straight away; other downgrades need two trading days in a row; re-running on the same day's prices never changes a label. Changes marked <b>rules updated</b> came from an improvement to the screener, not from the market.</p>`)}</div>`;
}
function horizonSection(d){
  if (!d.short_checks) return "";
  const hz = d.hz||{};
  const lab = v => v==="BUY" ? '<span class="sig BUY">BUY</span>' : v==="WATCH" ? '<span class="sig WATCH">WATCH</span>' : '<span class="sig HOLD">—</span>';
  const list = cs => cs.map(c=>`<div class="chk"><b class="${c.pass?"ok":"no"}">${c.pass?"✓":"✗"}</b><span>${c.label}</span></div>`).join("");
  return `<div class="sec"><h3>By time horizon</h3>
    <div class="grid"><div class="kv"><small>Short term (days–weeks)</small>${lab(hz.short)}</div><div class="kv"><small>Medium term (1–6 months)</small>${lab(hz.medium)}</div><div class="kv"><small>Long term (1 year+)</small>${lab(hz.long)}</div></div>
    <div class="fl" style="font-size:13px;font-weight:600;margin:10px 0 4px">Short-term checks (${d.short_checks.filter(c=>c.pass).length}/${d.short_checks.length})</div>${list(d.short_checks)}
    <div class="fl" style="font-size:13px;font-weight:600;margin:10px 0 4px">Long-term checks (${d.long_checks.filter(c=>c.pass).length}/${d.long_checks.length})</div>${list(d.long_checks)}
    ${why(`<p>Different investors care about different things. <b>Short term</b> looks for momentum and a fresh reason for the price to move (news, events, rising volume) and ignores valuation. <b>Medium term</b> is the main balanced score. <b>Long term</b> cares about the quality and financial strength of the business and whether it's reasonably priced, and mostly ignores short-term news.</p>
      <p>${hz.long==="BUY"&&hz.short!=="BUY"?"This looks like a solid long-term holding even if the short-term setup isn't there.":hz.short==="BUY"&&hz.long!=="BUY"?"This is a short-term momentum idea — the business itself doesn't pass the long-term quality tests, so it's not one to hold for years without a reason.":hz.short==="BUY"&&hz.long==="BUY"?"Rare: it passes both the short-term and long-term tests.":"It doesn't fully pass the short- or long-term tests right now; WATCH means one check short."}</p>`)}</div>`;
}
function dividendSection(d){
  const v = d.dividend; if(!v) return "";
  const c = CUR(d.market), kv = (l,x,cls="") => `<div class="kv"><small>${l}</small><b class="${cls}">${x}</b></div>`;
  const amt = x => x==null?"–":`${c} ${x<1?x.toFixed(3):x.toFixed(2)}`;
  if (!(v.yield>0) && !(v.hist||[]).length) return `<div class="sec"><h3>Dividends</h3><div class="mute">${esc(tk(d.ticker))} doesn't pay a dividend${v.years_paid===0?" (none in the last year)":""}. Companies that keep their profits usually reinvest them to grow — returns come from the share price only.</div></div>`;
  const today = new Date().toISOString().slice(0,10), yr = new Date().getFullYear();
  const hist = (v.hist||[]).slice(-8), mx = Math.max(...hist.map(h=>h[1]), 1e-9);
  const pay = v.payout, payCls = pay==null?"": pay>1?"bad": pay<=0.75?"good":"";
  return `<div class="sec"><h3>Dividends</h3>
    ${(v.tags||[]).length?`<div class="chips" style="margin:0 0 8px">${v.tags.map(t=>`<span class="chip ${t==="Dividend at risk"?"bad":"div-chip"}">${t}</span>`).join("")}</div>`:""}
    <div class="grid">
      ${kv("Dividend yield", v.yield!=null?v.yield.toFixed(2)+"%":"–", v.yield>=v.high_cut?"good":"")}
      ${kv("Paid in the last 12 months", amt(v.ttm)+" a share")}
      ${kv("Payout ratio (share of profit paid out)", pay!=null?Math.round(pay*100)+"%":"–", payCls)}
      ${kv("How often", v.freq||"–")}
      ${kv("Last dividend", v.last_date?`${amt(v.last_amt)} · ${v.last_date}`:"–")}
      ${kv(v.ex_date&&v.ex_date>=today?"Next ex-dividend date":"Last ex-dividend date", v.ex_date||"–", v.ex_date&&v.ex_date>=today?"good":"")}
      ${kv("Years in a row with a dividend", v.years_paid!=null?(v.years_paid>=10?"10+":v.years_paid):"–", v.years_paid>=5?"good":"")}
      ${kv("Years in a row it was raised", v.years_grew!=null?(v.years_grew>=9?"9+":v.years_grew):"–", v.years_grew>=5?"good":"")}
      ${v.avg5!=null?kv("5-year average yield", v.avg5.toFixed(2)+"%"):""}
    </div>
    ${hist.length?`<div class="fl" style="font-size:13px;font-weight:600;margin:12px 0 0">Dividends per share by year (${c})</div>
      <div class="dbar">${hist.map(([y,a])=>`<div><span>${a<1?a.toFixed(2):a.toFixed(1)}</span><i class="${y==yr?"part":""}" style="height:${Math.max(2,a/mx*70)}px"></i>${y}</div>`).join("")}</div>
      <div class="mute">Faded bar = ${yr} so far (not a full year). Special one-off dividends show as spikes.</div>`:""}
    ${(v.risk||[]).length?`<div style="margin-top:8px">${v.risk.map(x=>`<div class="chk"><b class="no">!</b><span>${esc(x)}</span></div>`).join("")}</div>`:""}
    ${why(`<p>The <b>dividend yield</b> is the cash paid out over the last year as a percentage of today's share price: a ${v.yield!=null?v.yield.toFixed(1):"–"}% yield means about ${c} ${v.yield!=null?(v.yield*10).toFixed(0):"–"} a year for every ${c} 1,000 invested, before tax.</p>
      <p>The <b>payout ratio</b> shows how much of the profit goes to dividends. Under about 75% leaves room to keep paying in a bad year; over 100% means the company pays more than it earns, which can't last.</p>
      <p>A long record of paying — and especially of <b>raising</b> — the dividend every year is the best sign it's dependable. To receive a dividend you must own the shares <b>before the ex-dividend date</b>.</p>
      ${d.market==="ASX"?"<p>Australian dividends often come with <b>franking credits</b> (tax already paid by the company), which are not included in the yield here — the real value to Australian residents can be higher.</p>":""}
      ${d.market==="PSX"?"<p>In Pakistan dividends are taxed at source (usually 15% for filers); the yield here is before tax.</p>":""}
      <p class="mute">Labels: <b>Dividend</b> = yield 2%+ and paid every year for at least 3 years. <b>High dividend</b> = in the top fifth of this market's dividend payers and at least ${v.high_cut}%. <b>Dividend grower</b> = raised 5+ years in a row. <b>Dividend at risk</b> = paying more than it earns, a loss, news of a cut, or a yield so high the market seems to expect a cut.</p>`)}</div>`;
}
function halalSection(d){
  const h = d.halal; if(!h) return "";
  const cls = h.status==="HALAL"?"good":h.status==="NOT HALAL"?"bad":"";
  const r = h.ratios||{};
  const row = (l,v,lim) => v==null ? `<tr><td>${l}</td><td>–</td><td>${lim}</td></tr>` : `<tr><td>${l}</td><td class="${v<parseFloat(lim)/100?"good":"bad"}">${(v*100).toFixed(1)}%</td><td>${lim}</td></tr>`;
  return `<div class="sec"><h3>Shariah screen: <span class="${cls}">${h.status}</span></h3>
    ${h.reasons.map(x=>`<div class="chk"><b class="${cls==="good"?"ok":cls==="bad"?"no":"skip"}">${cls==="good"?"✓":cls==="bad"?"✗":"?"}</b><span>${esc(x)}</span></div>`).join("")}
    ${h.method==="AAOIFI"&&(r.debt!=null||r.cash!=null)?`<table style="margin-top:8px"><tr><th>AAOIFI test</th><th>${tk(d.ticker)}</th><th>Limit</th></tr>
      ${row("Interest-bearing debt / market value", r.debt, "30%")}${row("Cash & interest investments / market value", r.cash, "30%")}${row("Interest income / revenue", r.interest_income, "5%")}</table>`:""}
    ${h.purification?`<div class="mute" style="margin-top:6px">Purification: give about <b>${(h.purification*100).toFixed(2)}%</b> of dividends/gains to charity.</div>`:""}
    ${h.method==="ASSET"?why(`<p>${d.market==="CRYPTO"?"There is no official Shariah list for cryptocurrencies and scholars differ. Some accept major coins with real use as permissible digital assets; others reject cryptocurrency altogether. Tokens whose value comes from interest-based lending are not permissible, and meme coins are widely seen as excessive speculation.":"Commodities themselves are permissible, but how you buy them matters: gold and silver must be bought spot — paid in full and delivered (or a fully bullion-backed, Shariah-certified product). Futures, options, leverage and short-selling are not permissible according to most scholars, and many commodity ETFs are built on futures."}</p>
      <p><b>HALAL</b> = permissible when bought the right way (see above). <b>DOUBTFUL</b> = depends on the product or scholars differ. <b>NOT HALAL</b> = fails a basic test.</p>
      <p class="mute">This is a simple automated guide, not a religious ruling. Check with a scholar or a Shariah screening service before investing.</p>`):why(`<p>${h.method==="KMI"?"For Pakistan this uses the <b>KMI All-Share Islamic Index</b> published by the Pakistan Stock Exchange, whose members are screened by Shariah advisors — the most reliable source available.":"For US and Australian stocks there's no free official list, so this applies the <b>AAOIFI</b> standard used by most Islamic funds: the company's main business must be permissible (no conventional banking/insurance, alcohol, tobacco, gambling, pork, adult content or weapons), its interest-bearing debt and its cash/interest-bearing investments must each be under 30% of its market value, and interest income must be under 5% of revenue."}</p>
      <p><b>HALAL</b> = passes every test. <b>DOUBTFUL</b> = permissible business but some data is missing or the industry often has mixed revenue — check the company's revenue breakdown. <b>NOT HALAL</b> = fails a test.</p>
      <p class="mute">This is an automated screen, not a religious ruling. Scholars differ on some thresholds; confirm with a Shariah-compliance service (e.g. Zoya, Musaffa, Islamicly) or a scholar before investing.</p>`)}</div>`;
}
function healthSection(d){
  const h = d.health; if(!h) return "";
  const tests = Object.entries(h.f_tests||{});
  const z = h.altman_z, zone = z==null?null: z>=3?["Safe","good"]: z>=1.8?["Grey zone",""]:["Distress zone","bad"];
  const kv = (l,v,c="") => `<div class="kv"><small>${l}</small><b class="${c}">${v}</b></div>`;
  return `<div class="sec"><h3>Financial health</h3>
    <div class="grid">
      ${kv(d.market==="PSX"?"Health score (partial)":"Piotroski F-score", h.f_score!=null?`${h.f_score} / 9`:"–", h.f_score>=7?"good":h.f_score!=null&&h.f_score<=3?"bad":"")}
      ${kv("Bankruptcy risk (Altman Z)", h.financial?"n/a for banks":z!=null?`${z} · ${zone[0]}`:"–", zone?zone[1]:"")}
      ${kv("Interest cover", h.interest_cover!=null?`${h.interest_cover}×`:"–", h.interest_cover==null?"":h.interest_cover>=5?"good":h.interest_cover<1.5?"bad":"")}
      ${kv("Cash vs reported profit", h.cash_conversion!=null?`${h.cash_conversion}×`:"–", h.cash_conversion==null?"":h.cash_conversion>=1?"good":h.cash_conversion<0.7?"bad":"")}
      ${kv("New shares issued (1y)", h.dilution!=null?fp(h.dilution):"–", h.dilution==null?"":h.dilution<=0.02?"good":h.dilution>0.1?"bad":"")}
      ${kv("Operating margin trend (2y)", h.margin_trend!=null?(h.margin_trend>0?"+":"")+(h.margin_trend*100).toFixed(1)+" pts":"–", h.margin_trend==null?"":h.margin_trend>0?"good":"bad")}
    </div>
    ${tests.length?`<div style="margin-top:10px">${tests.map(([k,v])=>`<div class="chk"><b class="${v?"ok":"no"}">${v?"✓":"✗"}</b><span>${esc(k)}</span></div>`).join("")}</div>`:`<div class="mute" style="margin-top:8px">Financial statements not available for this company.</div>`}
    ${why(xHealth(d))}</div>`;
}
function xHealth(d){
  const h = d.health, f = h.f_score;
  if (f==null && h.altman_z==null) return "";
  const fs = f==null?"":f>=7?`An F-score of <b>${f}/9</b> is <b>strong</b> — most signs in the latest accounts point to an improving, healthy business.`:f>=4?`An F-score of <b>${f}/9</b> is <b>middling</b> — a mix of improving and worsening signs.`:`An F-score of <b>${f}/9</b> is <b>weak</b> — most signs in the accounts are getting worse.`;
  const z = h.financial ? "Bankruptcy-risk scores don't work for banks and insurers, so it's skipped." : h.altman_z==null ? "" : h.altman_z>=3 ? "The Altman Z-score says bankruptcy risk is <b>low</b>." : h.altman_z>=1.8 ? "The Altman Z-score is in the <b>grey zone</b> — not alarming, but worth keeping an eye on." : "The Altman Z-score is in the <b>distress zone</b>, which historically signals elevated bankruptcy risk.";
  const ic = h.interest_cover==null?"":h.interest_cover<1.5?` Its operating profit only covers interest payments <b>${h.interest_cover}×</b> — debt is a real burden.`:h.interest_cover>=5?` Operating profit covers interest <b>${h.interest_cover}×</b>, so debt is easily manageable.`:"";
  const cc = h.cash_conversion==null?"":h.cash_conversion<0.7?` Cash coming in is well below reported profit (${h.cash_conversion}×), which can mean profits are "on paper" rather than in the bank.`:h.cash_conversion>=1?" Cash coming in matches or exceeds reported profit — a good sign the profits are real.":"";
  const dl = h.dilution==null?"":h.dilution>0.1?` It issued <b>${fp(h.dilution)}</b> more shares last year, which shrinks each existing shareholder's slice.`:"";
  return `<p>${fs} ${z}${ic}${cc}${dl}</p><p class="mute">${d.market==="PSX"?"For Pakistan only profit and EPS history are available, so this is a partial version of the test.":"The F-score runs 9 yes/no tests on the last two years of the income statement, balance sheet and cash-flow statement. Data refreshes weekly."}</p>`;
}
/* ---------- plain-English explanations ---------- */
function why(html, title="What this means"){ return html ? `<details class="why"><summary>${title}</summary>${html}</details>` : ""; }
const P = v => v==null ? "–" : Math.round(v*100)+"%";
const rankWord = v => v>=80?"among the best":v>=60?"above average":v>=40?"about average":v>=20?"below average":"among the weakest";
function xOverview(d){
  const top = Math.max(0, Math.round((d.of - d.rank)/d.of*100));
  const parts = [...d.parts].sort((a,b)=>b.value-a.value);
  return `<p><b>${esc(d.name)}</b> scores <b>${d.score}</b> out of 100, which puts it at <b>#${d.rank} of ${d.of}</b> ${ASSET(d.market)?NOUN(d.market):d.market+" stocks"} — better than about ${top}% of them.
    Its strongest area is <b>${parts[0].label.toLowerCase()}</b> (${parts[0].value}/100) and its weakest is <b>${parts[parts.length-1].label.toLowerCase()}</b> (${parts[parts.length-1].value}/100).
    ${mainLabel(dRow(d))?`The label is <b>${mainLabel(dRow(d))}</b>: ${LABEL_INFO[mainLabel(dRow(d))]}.`:"It has no label: nothing notable either way right now."}${(d.flags||[]).includes("REBOUND")?" It's also flagged <b>REBOUND</b>: a decent company whose price has fallen hard recently, which sometimes bounces back.":""}${(d.flags||[]).includes("TAKE PROFIT")?" It's flagged <b>TAKE PROFIT</b>: it has risen a lot very quickly and the support behind the move is fading.":""}</p>`;
}
function xLabel(d){
  const failB = d.checks.filter(c=>!c.pass&&!c.skipped).map(c=>c.label.toLowerCase());
  const passS = (d.sell_checks||[]).filter(c=>c.pass&&!c.skipped).map(c=>c.label.toLowerCase());
  const sg = d.signal||"HOLD";
  let t = "";
  const A = ASSET(d.market);
  if (A && sg==="BUY") t = "Every buy check passes: it's highly ranked, the price is trending up without being overheated, and the news and macro backdrop aren't hurting it.";
  else if (A && sg==="SELL") t = "It fails on every front at once — low ranking, falling price, negative news and a negative price model. If you own it, the screener suggests getting out.";
  else if (A && sg==="AVOID" && !(d.red_flags||[]).length) t = "It's near the bottom of the rankings and in a downtrend. Not a good time to buy.";
  else if (sg==="BUY") t = "Every buy check passes: it's highly ranked, the price is trending up without being overheated, the business looks solid compared with similar companies, and the news backdrop isn't hurting it.";
  else if (sg==="WATCH") t = `It passes every buy check except one: <b>${failB.join(", ")}</b>. If that changes, it would become a BUY.`;
  else if (sg==="SELL") t = "It fails on every front at once — low ranking, falling price, weak business numbers, negative news and a negative price model. If you own it, the screener suggests getting out.";
  else if (sg==="AVOID") t = (d.red_flags||[]).length ? `There's recent serious bad news: <b>${d.red_flags.map(esc).join(", ")}</b>. Stocks often keep falling for a while after news like this, so it's safer to wait.` : "It's near the bottom of the rankings and its business numbers are weak compared with its sector. Not a good time to buy.";
  else t = `Nothing stands out. It fails ${failB.length} buy check${failB.length===1?"":"s"}${failB.length?` (${failB.slice(0,3).join(", ")}${failB.length>3?"…":""})`:""} and shows ${passS.length} of ${(d.sell_checks||[]).length} sell warnings.`;
  return `<p>${t}</p><p class="mute">✓ = passes, ✗ = fails, ! = warning present, – = not used in this market.</p>`;
}
function xScore(d, up){
  const L = d.parts.map(p=>`<li><b>${p.label}</b> ${p.value}/100 — ${rankWord(p.value)}.</li>`).join("");
  const v = d.sub;
  if (ASSET(d.market)) return `<p>Each part compares it with the other ${NOUN(d.market)} in the screener (100 = best). The total is a weighted average of the parts. There are no company accounts here, so the score is the price trend model, its own news, its group's news and the macro/political picture.</p><ul>${L}</ul>`;
  return `<p>Each part compares this stock with the other ${d.market} stocks (100 = best). The total is a weighted average of the parts.</p><ul>${L}</ul>
    <p>Inside fundamentals: it looks ${rankWord(v.value)} on <b>value</b> (how cheap it is vs its sector), ${rankWord(v.quality)} on <b>quality</b> (profitability and debt), ${rankWord(v.growth)} on <b>growth</b>${v.health!=null?`, and ${rankWord(v.health)} on <b>financial health</b>`:""}.
    ${d.analyst.rating?` Professional analysts' average view is <b>${esc(d.analyst.rating).replace("_"," ")}</b>${up!=null?`, with a price target ${pct(up)} from today`:""}.`:""}</p>`;
}
function xChart(d, base){
  const c = d.close, n = c.length; if(!n) return "";
  const last = c[n-1], m50 = sma(c,50)[n-1], m200 = sma(c,200)[n-1];
  const y0 = c[Math.max(0,n-252)], i0 = base.index[Math.max(0,n-252)], i1 = base.index[n-1];
  const yr = y0&&last ? last/y0-1 : null, ir = i0&&i1 ? i1/i0-1 : null;
  let trend = "";
  if (m50&&m200) trend = last>m50&&last>m200 ? (m50>m200?"a clear <b>uptrend</b> — the price is above both its short-term (50-day) and long-term (200-day) averages, and the short-term average is above the long-term one":"<b>recovering</b> — above both averages, but the longer trend hasn't fully turned up yet")
    : last<m50&&last<m200 ? (m50<m200?"a clear <b>downtrend</b> — below both averages, with the short-term average under the long-term one":"<b>weakening</b> — it has slipped below both averages")
    : last>m200 ? "a <b>long-term uptrend with a short-term dip</b> (above the 200-day average but below the 50-day)" : "<b>bouncing within a downtrend</b> (above the 50-day average but still below the 200-day)";
  return `<p>The chart shows ${trend}.</p>
    <p>Over the past year the stock is ${yr!=null?`<b>${pct(yr)}</b>`:"–"} versus ${ir!=null?`${pct(ir)} for the index`:"the index"}${yr!=null&&ir!=null?` — it has <b>${yr>ir?"beaten":"lagged"}</b> the market`:""}.</p>
    <p class="mute">How to read it: green = price, orange = 50-day average (short-term trend), blue = 200-day average (long-term trend), dashed grey = the whole market for comparison. Price above the lines is generally healthy; below them is weak.</p>`;
}
function xTech(d){
  const t = d.tech, rsi = t["RSI (14 day)"], vol = t["Volatility (annual)"], vs = t["Volume vs normal"], hi = t["Off 52-week high"], m12 = t["12-month momentum"];
  const r = rsi==null?"":rsi>70?`<b>RSI ${rsi}</b> means it has risen fast recently and may be <b>overheated</b> — short-term pullbacks are common from here.`:rsi<30?`<b>RSI ${rsi}</b> means it has fallen hard recently and may be <b>oversold</b> — sometimes a bounce follows.`:`<b>RSI ${rsi}</b> is in the normal range (30–70): neither overheated nor oversold.`;
  const v = vol==null?"":`It swings about <b>${Math.round(vol*100)}% a year</b>, which is ${vol>0.45?"<b>very volatile</b> — expect big moves":vol>0.28?"fairly volatile":"relatively calm"}.`;
  const vv = vs==null?"":vs>1.5?`Trading volume is <b>${vs.toFixed(1)}×</b> normal — something is attracting attention.`:vs<0.7?"Trading is quieter than usual.":"Trading volume is normal.";
  return `<p>${r}</p><p>${v} ${vv}</p><p>${m12!=null?`Over 12 months (excluding the last month) it's ${pct(m12)}; `:""}${hi!=null?`it's ${hi>-0.02?"at or near its 52-week high":Math.round(-hi*100)+"% below its 52-week high"}.`:""}</p>`;
}
function xFund(d){
  const f = Object.fromEntries(d.fund.map(x=>[x.label,x]));
  const cmp = x => x&&x.value!=null&&x.sector!=null ? (x.better==="high"? x.value>x.sector : x.value<x.sector) : null;
  const good = d.fund.filter(x=>cmp(x)===true).map(x=>x.label.toLowerCase()), bad = d.fund.filter(x=>cmp(x)===false).map(x=>x.label.toLowerCase());
  const pe = f["P/E (forward)"]; let pel = "";
  if (pe&&pe.value!=null&&pe.sector) { const r = pe.value/pe.sector-1; pel = `Investors pay <b>${pe.value.toFixed(1)}×</b> its expected yearly profit, vs ${pe.sector.toFixed(1)}× for a typical company in its sector — it's <b>${Math.abs(Math.round(r*100))}% ${r<0?"cheaper":"more expensive"}</b>. ${r<0?"Cheaper can mean a bargain, or that the market expects problems.":"A premium usually means the market expects faster growth."}`; }
  const de = f["Debt / equity"]; const del = de&&de.value!=null ? ` Debt is <b>${(de.value/100).toFixed(2)}×</b> shareholders' equity${de.value>200?" — <b>high</b>, which adds risk if business slows":de.value<50?" — low and comfortable":""}.` : "";
  return `<p>${pel}</p><p>Better than the sector on: <b>${good.join(", ")||"none"}</b>. Worse on: <b>${bad.join(", ")||"none"}</b>.${del}</p>
    <p class="mute">Profit margin = how much of each dollar of sales becomes profit. Return on equity = profit made per dollar shareholders have invested. Free-cash-flow yield = spare cash generated as a % of the company's value.</p>`;
}
function xNews(d){
  const n = d.news||[], pos = n.filter(x=>x.score>0.15).length, neg = n.filter(x=>x.score<-0.15).length, promo = n.filter(x=>x.quality==="promo").length;
  if (!n.length) return `<p>No headlines about this company in the last 10 days — so news isn't helping or hurting its score.</p>`;
  const ev = (d.events||[]).filter(e=>Math.abs(e.impact)>=0.3);
  return `<p>Out of ${n.length} recent headlines, <b>${pos} look positive</b> and <b>${neg} negative</b>; the rest are neutral. Newer headlines count more than older ones.</p>
    ${ev.length?`<p>Key events spotted: ${ev.map(e=>`<b style="color:${e.impact<0?"var(--neg)":"var(--acc)"}">${esc(e.label)}</b>`).join(", ")}. Events like these tend to move a share price for days or weeks.</p>`:""}
    <p>Competitors' news is ${d.peer_avg>0.05?"mostly positive, which can lift the whole group":d.peer_avg<-0.05?"mostly negative, which can drag the whole group down":"fairly neutral"}.${promo?` ${promo} headline${promo>1?"s are":" is"} from promotional sites and count${promo>1?"":"s"} half.`:""}</p>`;
}
function xMacro(d){
  const m = d.macro, ups = m.effects.filter(e=>e.effect>0).map(e=>esc(e.theme.replace(/^AI: /,""))), dns = m.effects.filter(e=>e.effect<0).map(e=>esc(e.theme.replace(/^AI: /,"")));
  return `<p>This looks at the bigger picture — news about its whole industry and political or economic events — rather than the company itself. Overall it's <b>${m.score>0.1?"a tailwind (helping)":m.score<-0.1?"a headwind (hurting)":"roughly neutral"}</b> for this stock right now.</p>
    ${ups.length?`<p>Helping: ${ups.join(", ")}.</p>`:""}${dns.length?`<p>Hurting: ${dns.join(", ")}.</p>`:""}
    <p class="mute">For example, a war tends to lift oil and defence stocks but hurt airlines; interest-rate cuts usually help property and tech.</p>`;
}
function xPeers(d){
  if (!d.peers.length) return "";
  const better = d.peers.filter(p=>p.score!=null && p.score < d.score).length;
  const best = [...d.peers].sort((a,b)=>b.score-a.score)[0];
  return `<p>Compared with its ${d.peers.length} largest competitors, ${esc(d.name)} scores higher than <b>${better}</b> of them.${best&&best.score>d.score?` The highest-scoring competitor is <b>${tk(best.ticker)}</b> (${best.score}) — worth a look if you like this sector.`:" It's the top scorer in this group."}</p>`;
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
function closeSheet(){ $("sheet").classList.remove("open"); document.body.style.overflow=""; render(); }
window.addEventListener("popstate", e => { if (e.state && e.state.t) openStock(e.state.t, false); else closeSheet(); });
const AUTH_HASH = /access_token=|refresh_token=|error=|error_code=|type=(magiclink|signup|recovery)/.test(location.hash);
if (location.hash.length > 1 && !AUTH_HASH) { history.replaceState(null, "", location.pathname); openStock(decodeURIComponent(location.hash.slice(1))); }
render();
dbInit();
loadExtras();
</script></body></html>"""


def write_page(payload, path):
    from events import BAD
    import config
    payload = dict(payload, db={"url": getattr(config, "SUPABASE_URL", ""), "key": getattr(config, "SUPABASE_ANON_KEY", "")})
    page = PAGE.replace("__BAD_EVENTS__", ",".join(json.dumps(b) for b in sorted(BAD)))
    with open(path, "w") as f:
        f.write(page.replace("__DATA__", json.dumps(payload, default=str, separators=(",", ":"))))
