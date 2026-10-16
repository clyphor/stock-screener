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
.sig.HOLD{border:1px solid var(--line);color:var(--mute);font-weight:600}
.sig.AVOID{border:1px solid var(--ma50);color:var(--ma50)}.sig.SELL{background:var(--neg);color:#fff}
.sig.flag{border:1px dashed var(--mute);color:var(--ink);font-weight:600}
.card.SELL{border:2px solid var(--neg)}
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
<div class="clock" id="clock"></div>
<details class="box" id="ovbox" open><summary><b style="color:var(--ink)">Market overview</b> <span id="ovsum"></span></summary><div id="ov" style="margin-top:8px"></div></details>
<input class="search" id="q" placeholder="Search any stock (e.g. CBA, Apple, OGDC)" autocomplete="off">
<div id="sigs" class="box"></div>
<details class="box" id="macrobox"><summary><b style="color:var(--ink)">Market &amp; politics today</b> <span id="macrosum"></span></summary><div id="macro" style="margin-top:8px"></div></details>
<details class="box" id="statsbox"><summary>How reliable is this? (backtest)</summary><div id="stats" style="margin-top:8px"></div></details>
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
const tk = t => t.replace(".AX","").replace(".KA","");
const pct = (v,d=1) => v==null ? "–" : (v>0?"+":"") + (v*100).toFixed(d) + "%";
const esc = s => String(s??"").replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
$("gen").textContent = "Updated " + new Date(D.generated).toLocaleString(undefined,{weekday:"short",day:"numeric",month:"short",hour:"numeric",minute:"2-digit",timeZoneName:"short"}) + (D.demo ? " · DEMO DATA" : "");

function badge(sg){ return sg ? `<span class="sig ${sg}">${sg}</span>` : ""; }
const LABEL_INFO = {
  BUY:"passes every buy check", WATCH:"one check short of a buy", HOLD:"no strong reason to buy or sell",
  AVOID:"recent red flag, or bottom-ranked with weak fundamentals — don't buy now", SELL:"fails on every front — exit if you own it"};
function card(r, i, extra=""){
  return `<div class="card ${r.signal||""}" onclick="openStock('${r.ticker}')">${extra}<div class="top"><div style="min-width:0"><span class="rank">${MINE(M)?r.market+" ":""}#${(r.rank||i+1)}</span><span class="tk">${tk(r.ticker)}</span>${badge(r.signal)}${(r.flags||[]).map(f=>`<span class="sig flag">${f}</span>`).join("")}
   <div class="nm">${esc(r.name)} · ${esc(r.sector)}</div></div><div class="sc">${r.score}</div></div>
   <div class="bars">${Object.entries(r.parts).map(([k,v])=>`<div class="bar"><small>${L[k]}</small><i><span style="width:${v}%"></span></i></div>`).join("")}</div>
   <div class="meta">Price ${r.price??"–"}${(r.market||M)==="PSX"?" PKR":""} · 3m ${r.ret3m??"–"}% · P/E ${r.pe??"–"}</div>
   <div class="chips">${r.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div></div>`;
}
function render(){
  [...$("tabs").children].forEach(b=>b.classList.toggle("on", b.textContent===M));
  const mine = MINE(M);
  ["clock","ovbox","sigs","macrobox","statsbox"].forEach(id=>$(id).style.display = mine ? "none" : "");
  $("mine").style.display = mine ? "" : "none";
  renderLog();
  if (mine) return renderMine();
  const s = D.stats[M]||{}, rows = D.markets[M]||[];
  const buys = rows.filter(r=>r.signal==="BUY"), watch = rows.filter(r=>r.signal==="WATCH");
  const sells = rows.filter(r=>r.signal==="SELL"), avoids = rows.filter(r=>r.signal==="AVOID");
  const reb = rows.filter(r=>(r.flags||[]).includes("REBOUND")), tp = rows.filter(r=>(r.flags||[]).includes("TAKE PROFIT"));
  const T = s.track||{};
  const trl = lab => T[lab] ? `${lab}: ${T[lab].n} past calls, right <b>${Math.round(T[lab].win_rate*100)}%</b> of the time (avg ${(T[lab].avg_excess*100).toFixed(2)}% vs index)` : null;
  const trs = ["BUY","SELL","AVOID"].map(trl).filter(Boolean);
  const link = r => `<a href="#" onclick="openStock('${r.ticker}');return false" style="color:inherit">${tk(r.ticker)}</a>`;
  const tr = trs.length ? "Scorecard — " + trs.join("; ") + "." : `Scorecard is building — check back in a week or two.`;
  $("sigs").innerHTML = s.error ? `<h2>${M} run failed</h2><div class="mute">${esc(s.error)}</div>` :
    `<h2>${buys.length ? "Buy signals: "+buys.map(link).join(", ") : "No buy signals today"}</h2>`
    + (watch.length ? `<div>Watch: ${watch.map(link).join(", ")}</div>` : "")
    + (sells.length ? `<div style="margin-top:4px"><b style="color:var(--neg)">Sell:</b> ${sells.slice(0,15).map(link).join(", ")}${sells.length>15?` +${sells.length-15} more`:""}</div>` : "")
    + (avoids.length ? `<div style="margin-top:4px"><b style="color:var(--ma50)">Avoid:</b> ${avoids.length} stocks <a href="#" onclick="quickSig('AVOID');return false" style="color:inherit">(show)</a></div>` : "")
    + (reb.length||tp.length ? `<div style="margin-top:4px">${reb.length?`Rebound: ${reb.slice(0,8).map(link).join(", ")}`:""}${reb.length&&tp.length?" · ":""}${tp.length?`Take profit: ${tp.slice(0,8).map(link).join(", ")}`:""}</div>` : "")
    + `<details class="why"><summary>What do the labels mean?</summary><ul>
        <li><b>BUY</b> — passes every check: top 15% score, uptrend, not overbought, solid fundamentals, no bad company/competitor news, no strong sector/political headwind${s.model_used ? ", price model agrees" : ""}.</li>
        <li><b>WATCH</b> — passes all but one buy check.</li><li><b>HOLD</b> — nothing notable either way.</li>
        <li><b>AVOID</b> — a red flag in the last 10 days (scandal/probe, profit warning, capital raising, CEO exit, debt stress, failed trial…) or a strong sector/political headwind, or bottom-ranked with weak fundamentals.</li>
        <li><b>SELL</b> — the mirror of BUY: bottom 15% score, downtrend, weak fundamentals, negative news, model negative.</li>
        <li><b>REBOUND</b> — good company that looks oversold (RSI under 30, no red flags). <b>TAKE PROFIT</b> — big run, overbought, support fading.</li></ul></details>
      <div class="mute" style="margin-top:6px">${tr}</div>`;
  $("stats").innerHTML = s.error ? "" :
    `Tested on ${s.test_from} onwards (data the model never saw): top-20% picks beat bottom-20% by <b>${((s.top_minus_bottom||0)*100).toFixed(2)}%</b> a month; ranking accuracy (IC) <b>${s.ic_mean}</b> (0 = random); top picks beat the index <b>${Math.round((s.top_hit_rate||0)*100)}%</b> of the time. ${s.screened} stocks passed the screen.<br><br><b>Data check:</b> prices up to the ${s.price_date||"–"} close (holidays not shown on the clock); ${Math.round((s.news_coverage||0)*100)}% of stocks had news in the last 10 days (scored by ${s.news_method}). AI scoring: <b>${s.ai_scoring==="on"||s.ai_scoring===true?"on":s.ai_scoring==="failed"?"FAILED today (out of API credit or key problem) — using free rules":"off — add an ANTHROPIC_API_KEY secret to turn it on"}</b>.${(s.news_coverage||0)<0.5?" <b>News coverage is low — treat the News and Peers parts with caution.</b>":""}`
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

/* ---------------- my watchlists & paper trades (saved on this device) ---------------- */
function store(key, def){ return {
  get(){ if(!this.v){ try{ this.v = JSON.parse(localStorage.getItem(key)) || def(); }catch(e){ this.v = def(); } } return this.v; },
  save(){ try{ localStorage.setItem(key, JSON.stringify(this.v)); }catch(e){ alert("Couldn't save on this device (private browsing?)"); } } }; }
const WL = store("watchlists", ()=>({lists:{"My watchlist":[]}, cur:"My watchlist"}));
const PT = store("paper_trades", ()=>[]);
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
function toggleInList(t, n){ const w=WL.get(); const a=w.lists[n]||(w.lists[n]=[]); const i=a.indexOf(t); i>=0?a.splice(i,1):a.push(t); WL.save(); closeModal(); addToList(t); }
function newList(n){ const w=WL.get(); if(!w.lists[n]) w.lists[n]=[]; w.cur=n; WL.save(); }

function paperBuy(t){
  const r = ALL[t]; if(!r) return alert("No current price for this stock.");
  const cur = {US:"US$",ASX:"A$",PSX:"PKR "}[r.market]||"";
  modal(`<h3 style="margin:0 0 4px">Paper buy ${tk(t)}</h3><div class="mute">Pretend purchase at the latest close: <b>${cur}${r.price}</b>. Label today: ${badge(r.signal||"HOLD")} score ${r.score}.</div>
    <label class="mute" style="display:block;margin-top:10px">Amount to invest (${cur.trim()})</label><input id="amt" inputmode="decimal" value="${r.market==="PSX"?100000:1000}">
    <label class="mute">Note (optional)</label><input id="nt" placeholder="Why I'm buying">
    <div class="btnrow"><button class="sbtn pri" onclick="doPaperBuy('${t}')">Buy (paper)</button><button class="sbtn" onclick="closeModal()">Cancel</button></div>`);
}
function doPaperBuy(t){
  const r = ALL[t], amt = Number($("amt").value)||0; if(amt<=0) return;
  const s = D.stats[r.market]||{};
  PT.get().unshift({id:Date.now(), ticker:t, market:r.market, date:s.price_date||D.generated.slice(0,10), price:r.price, idx:s.index_level,
    label:r.signal||"HOLD", flags:r.flags||[], score:r.score, amount:amt, shares:amt/r.price, note:$("nt").value.trim(), status:"open"});
  PT.save(); closeModal(); alert(`Paper bought ${tk(t)}. See the Paper tab.`);
}
function paperSell(id){
  const x = PT.get().find(z=>z.id===id), r = ALL[x.ticker], s = D.stats[x.market]||{};
  if(!r) return alert("No current price — can't close today.");
  if(!confirm(`Close ${tk(x.ticker)} at ${r.price}?`)) return;
  Object.assign(x, {status:"closed", exit_price:r.price, exit_date:s.price_date, exit_idx:s.index_level, exit_label:r.signal||"HOLD"}); PT.save(); render();
}
function paperDel(id){ if(!confirm("Delete this paper trade?")) return; PT.v = PT.get().filter(z=>z.id!==id); PT.save(); render(); }
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
function doImport(){ const f=$("imf").files[0]; if(!f) return; f.text().then(txt=>{ try{ const j=JSON.parse(txt); if(j.watchlists){WL.v=j.watchlists;WL.save();} if(j.paper){PT.v=j.paper;PT.save();} closeModal(); render(); }catch(e){ alert("That file isn't a valid backup."); } }); }

function renderMine(){
  const F = getF(), q = $("q").value.trim().toLowerCase();
  const backup = `<div class="mute" style="margin-top:8px;font-size:12px">Saved on this phone/browser only. <a href="#" onclick="exportData();return false" style="color:var(--acc)">Back up</a> · <a href="#" onclick="importData();return false" style="color:var(--acc)">Restore</a></div>`;
  let rows = rowsFor(M);
  if (q) rows = rows.filter(r=>r.ticker.toLowerCase().startsWith(q) || (r.name||"").toLowerCase().includes(q));
  const active = activeCount(F);
  const key = SORTS[F.sort] ? F.sort : "score";
  $("fbtn").textContent = active ? `Filters (${active})` : "Filters"; $("fbtn").classList.toggle("on", !!active);
  $("freset").style.display = active ? "block" : "none"; $("sortbtn").textContent = "Sort: " + SORTS[key].l;
  $("more").style.display = "none";
  if ($("fpanel").classList.contains("open")) drawPanel();
  if (M==="Lists"){
    const w = WL.get(), names = Object.keys(w.lists);
    if (!w.lists[w.cur]) w.cur = names[0];
    $("mine").innerHTML = `<div class="mine-head"><b>Watchlists</b><div class="pills" style="margin-top:8px">${names.map(n=>`<button class="pill ${n===w.cur?"on":""}" onclick="WL.get().cur=decodeURIComponent('${encodeURIComponent(n)}');WL.save();render()">${esc(n)} (${w.lists[n].length})</button>`).join("")}</div>
      <div class="btnrow"><button class="sbtn" onclick="const n=prompt('New list name'); if(n&&n.trim()){ newList(n.trim()); render(); }">+ New list</button>
      ${w.cur?`<button class="sbtn" onclick="const n=prompt('Rename list', WL.get().cur); if(n&&n.trim()&&n!==WL.get().cur){ const w=WL.get(); w.lists[n.trim()]=w.lists[w.cur]; delete w.lists[w.cur]; w.cur=n.trim(); WL.save(); render(); }">Rename</button>
      <button class="sbtn neg" onclick="if(confirm('Delete this list?')){ const w=WL.get(); delete w.lists[w.cur]; if(!Object.keys(w.lists).length) w.lists['My watchlist']=[]; w.cur=Object.keys(w.lists)[0]; WL.save(); render(); }">Delete list</button>`:""}</div>
      <div class="mute" style="margin-top:8px">Add stocks from any market: open a stock and tap ☆ Watchlist.</div>${backup}</div>`;
    let shown = rows.filter(r=>passes(r,F)); if (key!=="score") shown.sort((a,b)=>SORTS[key].f(a,b)); else shown.sort((a,b)=>b.score-a.score);
    const missing = (w.lists[w.cur]||[]).filter(t=>!ALL[t]);
    $("count").textContent = `${shown.length} of ${(w.lists[w.cur]||[]).length} stocks${active?" match":""}`;
    $("list").innerHTML = shown.map((r,i)=>card(r,i,`<button class="cardx" onclick="event.stopPropagation(); const w=WL.get(); w.lists[w.cur]=w.lists[w.cur].filter(x=>x!=='${r.ticker}'); WL.save(); render();" title="Remove">✕</button>`)).join("")
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
  const byLab = {}; done.forEach(z=>{ (byLab[z.x.label] ||= []).push(z); });
  if (key!=="score") {} 
  S.sort((a,b)=> (b.x.id - a.x.id));
  $("mine").innerHTML = `<div class="mine-head"><b>Paper trades</b>
    <div class="pills" style="margin-top:8px">${[["all","All"],["open","Open"],["closed","Closed"]].map(([v,l])=>`<button class="pill ${st===v?"on":""}" onclick="getF().st='${v}';saveF();render()">${l} (${v==="all"?all.length:all.filter(x=>x.status===v).length})</button>`).join("")}</div>
    ${done.length?`<div class="grid" style="margin-top:10px">
      <div class="kv"><small>Average return</small><b class="${avg(done.map(z=>z.ret))>=0?"good":"bad"}">${fp(avg(done.map(z=>z.ret)))}</b></div>
      <div class="kv"><small>Average vs index</small><b class="${avg(done.map(z=>z.vs).filter(v=>v!=null))>=0?"good":"bad"}">${fp(avg(done.map(z=>z.vs).filter(v=>v!=null)))}</b></div>
      <div class="kv"><small>Beat the index</small><b>${wins} of ${done.length} (${Math.round(wins/done.length*100)}%)</b></div>
      <div class="kv"><small>Total P&amp;L</small><b>${(()=>{ const byCur={}; done.forEach(z=>{ const c={US:"US$",ASX:"A$",PSX:"PKR "}[z.x.market]; byCur[c]=(byCur[c]||0)+z.x.amount*z.ret; }); return Object.entries(byCur).map(([c,v])=>`${v>=0?"+":"−"}${c}${Math.abs(v).toFixed(0)}`).join(" · "); })()}</b></div></div>
      <div class="mute" style="margin-top:8px">By label when bought: ${Object.entries(byLab).map(([l,a])=>`${l} ${fp(avg(a.map(z=>z.vs).filter(v=>v!=null)))} vs index (${a.length})`).join(" · ")}</div>`:`<div class="mute" style="margin-top:8px">No paper trades yet. Open a stock and tap “Paper buy” to test a signal.</div>`}
    ${backup}</div>`;
  $("count").textContent = active||q ? `${trades.length} of ${all.length} trades match` : "";
  const cur = m => ({US:"US$",ASX:"A$",PSX:"PKR "})[m]||"";
  $("list").innerHTML = S.map(({x,px,ret,vs,iret,days,now})=>`<div class="trade">
    <div class="row"><div><span class="tk" onclick="openStock('${x.ticker}')" style="cursor:pointer">${tk(x.ticker)}</span> <span class="mute">${x.market}</span> ${x.status==="closed"?'<span class="sig HOLD">CLOSED</span>':""}</div>
      <div class="big2 ${ret>=0?"good":"bad"}">${fp(ret)}</div></div>
    <div class="mute">${esc(now?.name||"")}</div>
    <div style="font-size:13px;margin-top:6px">Bought ${x.date} at ${cur(x.market)}${x.price} as ${badge(x.label)} (score ${x.score}) · ${x.status==="closed"?`sold ${x.exit_date} at ${cur(x.market)}${x.exit_price}`:`now ${cur(x.market)}${px??"–"} ${now?badge(now.signal||"HOLD"):""}`}</div>
    <div style="font-size:13px;margin-top:4px">Index ${fp(iret)} over the same ${days} days → <b class="${vs>=0?"good":"bad"}">${fp(vs)} vs index</b> · ${cur(x.market)}${x.amount} invested → ${ret!=null?`${ret>=0?"+":"−"}${cur(x.market)}${Math.abs(x.amount*ret).toFixed(0)}`:"–"}</div>
    ${x.note?`<div class="mute" style="margin-top:4px">“${esc(x.note)}”</div>`:""}
    <div class="btnrow">${x.status==="open"?`<button class="sbtn" onclick="paperSell(${x.id})">Close (sell)</button>`:""}<button class="sbtn" onclick="openStock('${x.ticker}')">Details</button><button class="sbtn neg" onclick="paperDel(${x.id})">Delete</button></div></div>`).join("");
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
  $("runlog").innerHTML = LOG.slice(0,12).map(l=>`<div class="logrow"><b class="st-${l.status}">${l.status.toUpperCase()}</b> · ${when(l.started)} · ${l.minutes} min · ${l.trigger==="schedule"?"scheduled":"manual"}
    <div class="mute">${Object.entries(l.markets||{}).map(([m,v])=>v.error?`${m}: <b class="bad">failed</b> — ${esc(v.error)}`:`${m}: ${v.screened}/${v.downloaded} stocks, news ${Math.round((v.news_coverage||0)*100)}%, AI ${v.ai_scoring}${v.ai_events?` (${v.ai_events} events)`:""}${(v.missing_prices||[]).length?`, no prices for ${v.missing_prices.length}`:""}`).join("<br>")}</div>
    ${l.fatal?`<div class="bad">${esc(l.fatal)}</div>`:""}
    ${(l.warnings||[]).length?`<details><summary class="mute" style="font-size:12px">${l.warnings.length} warning(s)</summary><div class="mute" style="font-size:12px;white-space:pre-wrap">${l.warnings.map(esc).join("\n")}</div></details>`:""}</div>`).join("")
    + `<div class="mute" style="margin-top:6px;font-size:12px">Full logs are kept in the repo under results/logs.</div>`;
}

/* ---------------- market overview ---------------- */
const PER = ["1D","1W","1M","3M","YTD","1Y","5Y"];
const fp = v => v==null ? "–" : (v>0?"+":"") + (v*100).toFixed(Math.abs(v)<0.1?1:0) + "%";
function heatBg(v, lab){ if(v==null) return "transparent"; const scale = {"1D":0.03,"1W":0.06,"1M":0.12,"3M":0.2,"YTD":0.3,"1Y":0.4,"5Y":1}[lab]||0.2;
  const a = Math.min(1, Math.abs(v)/scale)*0.55+0.08; return v>=0 ? `rgba(70,160,110,${a})` : `rgba(200,90,70,${a})`; }
function renderOverview(s){
  const p = s.perf; if(!p){ $("ov").innerHTML = '<div class="mute">Not available yet — appears after the next run.</div>'; $("ovsum").textContent=""; return; }
  const idxName = {US:"S&P 500 (SPY)", ASX:"ASX 200", PSX:"KSE-100 (built from members)"}[M] || "Index";
  $("ovsum").innerHTML = `· today <b style="color:${(p.index["1D"]||0)>=0?"var(--acc)":"var(--neg)"}">${fp(p.index["1D"])}</b> · 1Y ${fp(p.index["1Y"])}`;
  const sec = p.sectors, ind = p.industries;
  const best = ind.slice(0,5), worst = ind.slice(-5).reverse();
  $("ov").innerHTML = `<div class="mute">${idxName}</div>
    <div class="perf">${PER.map(k=>`<div style="background:${heatBg(p.index[k],k)}"><small>${k}</small><b>${fp(p.index[k])}</b></div>`).join("")}</div>
    <div class="mute" style="margin:4px 0">Sectors (weighted by company size) — tap one to filter:</div>
    <div class="heatwrap"><table class="heat"><tr><th></th>${PER.map(k=>`<th>${k}</th>`).join("")}</tr>
    ${sec.map(r=>`<tr><td onclick="sectorFilter('${esc(r.name).replace(/'/g,"\\'")}')"><b style="font-weight:600">${esc(r.name)}</b> <span class="mute">${r.n}</span></td>${PER.map(k=>`<td style="background:${heatBg(r.ret[k],k)}">${fp(r.ret[k])}</td>`).join("")}</tr>`).join("")}</table></div>
    <div class="mute" style="font-size:11px;margin-top:2px">Swipe the table sideways for 1Y and 5Y.</div>
    ${ind.length?`<div class="grid" style="margin-top:10px"><div><div class="mute" style="margin-bottom:4px">Best industries (1M)</div>${best.map(r=>`<div style="font-size:13px;display:flex;justify-content:space-between;gap:6px"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.name)}</span><b class="good">${fp(r.ret["1M"])}</b></div>`).join("")}</div>
      <div><div class="mute" style="margin-bottom:4px">Worst industries (1M)</div>${worst.map(r=>`<div style="font-size:13px;display:flex;justify-content:space-between;gap:6px"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.name)}</span><b class="bad">${fp(r.ret["1M"])}</b></div>`).join("")}</div></div>`:""}
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
};
const DEF = () => ({mk:[], flg:[], sig:[], sec:[], smin:"", smax:"", parts:{}, pemin:"", pemax:"", rmin:"", rmax:"", rsimin:"", rsimax:"",
  cap:"", news:"", macro:"", good:[], bad:[], tags:[], sort:"score", vqmin:{}});
const FS = {};
function getF(){ if(!FS[M]){ try{ FS[M] = Object.assign(DEF(), JSON.parse(localStorage.getItem("f_"+M)||"{}")); }catch(e){ FS[M]=DEF(); } FS[M].sig = (FS[M].sig||[]).map(x=>x==="NONE"?"HOLD":x); } return FS[M]; }
function saveF(){ try{ localStorage.setItem("f_"+M, JSON.stringify(FS[M])); }catch(e){} }
const num = v => v===""||v==null ? null : Number(v);
function activeCount(F){ let n=0;
  if(F.sig.length) n++; if((F.flg||[]).length) n++; if((F.mk||[]).length) n++; if(F.sec.length) n++; if(F.smin!==""||F.smax!=="") n++;
  n += Object.values(F.parts).filter(v=>v>0).length; n += Object.values(F.vqmin).filter(v=>v>0).length;
  if(F.pemin!==""||F.pemax!=="") n++; if(F.rmin!==""||F.rmax!=="") n++; if(F.rsimin!==""||F.rsimax!=="") n++;
  if(F.cap) n++; if(F.news) n++; if(F.macro) n++; n += F.good.length?1:0; n += F.bad.length?1:0; n += F.tags.length?1:0; return n; }
function passes(r, F){
  if ((F.mk||[]).length && !F.mk.includes(r.market)) return false;
  if (F.sig.length){ const sg = r.signal||"HOLD"; if(!F.sig.includes(sg)) return false; }
  if ((F.flg||[]).length && !F.flg.some(f=>(r.flags||[]).includes(f))) return false;
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
  const caps = M==="US" ? [["",'Any'],["1e10",">$10B"],["5e10",">$50B"],["2e11",">$200B"],["-2e10","<$20B"]]
             : M==="ASX" ? [["",'Any'],["2e9",">A$2B"],["1e10",">A$10B"],["5e10",">A$50B"],["-5e9","<A$5B"]]
             : [["",'Any'],["5e10",">PKR 50B"],["2e11",">PKR 200B"],["5e11",">PKR 500B"],["-5e10","<PKR 50B"]];
  $("fpanel").innerHTML = `
   ${MINE(M)?`<div class="fg"><span class="fl">Market</span>${pills("mk",MARKETS.map(m=>[m,m]),F.mk||[])}</div>`:""}
   <div class="fg"><span class="fl">Signal</span>${pills("sig",[["BUY","BUY"],["WATCH","WATCH"],["HOLD","HOLD"],["AVOID","AVOID"],["SELL","SELL"]],F.sig)}
     <div class="mute" style="margin-top:4px">Tap several to combine, e.g. BUY + WATCH.</div></div>
   <div class="fg"><span class="fl">Flags</span>${pills("flg",[["REBOUND","REBOUND (oversold quality)"],["TAKE PROFIT","TAKE PROFIT"]],F.flg)}</div>
   <div class="fg"><span class="fl">Sector</span>${pills("sec",secs.map(x=>[x,x]),F.sec)}</div>
   <div class="fg"><span class="fl">Overall score</span>${rng("smin","smax","min e.g. 60","max")}</div>
   <div class="fg"><span class="fl">Minimum part scores (0–100 rank)</span>
     ${PARTS.map(([k,l])=>`<div class="sl"><span>${l}</span><input type="range" min="0" max="95" step="5" value="${F.parts[k]||0}" oninput="this.nextElementSibling.textContent=this.value" onchange="F_part('${k}',this.value)"><b>${F.parts[k]||0}</b></div>`).join("")}
     ${[["value","Value vs sector"],["quality","Quality"],["growth","Growth"],["health","Financial health"]].map(([k,l])=>`<div class="sl"><span>${l}</span><input type="range" min="0" max="95" step="5" value="${F.vqmin[k]||0}" oninput="this.nextElementSibling.textContent=this.value" onchange="F_vq('${k}',this.value)"><b>${F.vqmin[k]||0}</b></div>`).join("")}</div>
   <div class="fg"><span class="fl">Company news</span>${one("news",[["","Any"],["pos","Positive"],["notneg","Not negative"],["neg","Negative"],["has","Has news"]],F.news)}</div>
   <div class="fg"><span class="fl">Sector & politics</span>${one("macro",[["","Any"],["tail","Tailwind"],["nohead","No headwind"],["head","Headwind"]],F.macro)}</div>
   ${good.length?`<div class="fg"><span class="fl">Has a recent event (any of)</span>${pills("good",good.map(x=>[x,x]),F.good)}</div>`:""}
   ${bad.length?`<div class="fg"><span class="fl">Exclude stocks with</span>${pills("bad",bad.map(x=>[x,x]),F.bad,true)}</div>`:""}
   <div class="fg"><span class="fl">P/E</span>${rng("pemin","pemax","min","max e.g. 20")}</div>
   <div class="fg"><span class="fl">3-month return %</span>${rng("rmin","rmax","min e.g. 0","max")}</div>
   <div class="fg"><span class="fl">RSI (14 day)</span>${rng("rsimin","rsimax","min","max e.g. 70")}<div class="mute" style="margin-top:4px">Under 30 = oversold, over 70 = overbought.</div></div>
   ${MINE(M)?"":`<div class="fg"><span class="fl">Market cap</span>${one("cap",caps,F.cap)}</div>`}
   ${tags.length?`<div class="fg"><span class="fl">Must have all of these tags</span>${pills("tags",tags.map(x=>[x,x]),F.tags)}</div>`:""}
   <div class="fg"><label>Sort by</label><select onchange="setF('sort',this.value)">${Object.entries(SORTS).map(([k,v])=>`<option value="${k}" ${F.sort===k?"selected":""}>${v.l}</option>`).join("")}</select></div>
   <div class="fact"><button onclick="resetF()">Clear all</button><button class="pri" onclick="$('fpanel').classList.remove('open');window.scrollTo({top:$('count').offsetTop-60,behavior:'smooth'})">Show ${rowsFor(M).filter(r=>passes(r,F)).length} stocks</button></div>`;
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

$("more").onclick = ()=>{ showAll=!showAll; render(); };
$("q").oninput = render;
const MARKETS = Object.keys(D.markets);
[...MARKETS, "Lists", "Paper"].forEach(m=>{const b=document.createElement("button");b.textContent=m;b.onclick=()=>{M=m;showAll=false;$("q").value="";$("fpanel").classList.remove("open");render()};$("tabs").appendChild(b)});
const MINE = v => v==="Lists" || v==="Paper";
/* every stock from every market, keyed by ticker, with its market and rank */
const ALL = {};
MARKETS.forEach(m => (D.markets[m]||[]).forEach((r,i)=>{ ALL[r.ticker] = Object.assign({market:m, rank:i+1}, r); }));
function rowsFor(view){
  if (view==="Lists") return (WL.get().lists[WL.get().cur]||[]).map(t=>ALL[t]).filter(Boolean);
  if (view==="Paper") return [...new Set(PT.get().map(x=>x.ticker))].map(t=>ALL[t]).filter(Boolean);
  return (D.markets[view]||[]).map((r,i)=>Object.assign({market:view, rank:i+1}, r));
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
  sh.innerHTML = `<div class="shead"><button class="back" onclick="history.back()">‹ Back</button><b>${tk(d.ticker)}</b>${badge(d.signal)}${(d.flags||[]).map(f=>`<span class="sig flag">${f}</span>`).join("")}</div>
  <div class="sec"><div class="hero"><div style="min-width:0"><div class="tk" style="font-size:20px">${esc(d.name)}</div>
    <div class="mute">${esc(d.sector)}${d.industry?" · "+esc(d.industry):""}</div>
    <div style="margin-top:8px">Price <b>${d.price??"–"}${d.market==="PSX"?" PKR":""}</b> · Market cap <b>${fmtCap(d.mcap)}${d.market==="PSX"?" PKR":""}</b></div></div>
    <div style="text-align:right"><div class="big">${d.score}</div><div class="mute">#${d.rank} of ${d.of}</div></div></div>
    <div class="chips" style="margin-top:8px">${d.reasons.map(x=>`<span class="chip ${BAD.includes(x)?"bad":""}">${x}</span>`).join("")}</div>
    <div class="btnrow"><button class="sbtn" onclick="addToList('${d.ticker}')">☆ Watchlist</button><button class="sbtn pri" onclick="paperBuy('${d.ticker}')">Paper buy</button></div>
    ${why(xOverview(d), "In plain English")}</div>

  <div class="sec"><h3>Label: ${badge(d.signal||"HOLD")} <span class="mute" style="font-weight:400">${LABEL_INFO[d.signal||"HOLD"]}</span></h3>
    ${(d.red_flags||[]).length?`<div style="margin-bottom:8px"><b style="color:var(--neg)">Red flags:</b> ${d.red_flags.map(esc).join(", ")}</div>`:""}
    <div class="fl" style="font-size:13px;font-weight:600;margin:4px 0">Buy checks (${d.checks.filter(c=>c.pass||c.skipped).length}/${d.checks.length})</div>
    ${d.checks.map(c=>`<div class="chk"><b class="${c.skipped?"skip":c.pass?"ok":"no"}">${c.skipped?"–":c.pass?"✓":"✗"}</b><span>${c.label}${c.skipped?' <span class="mute">(not used: model failed its test in this market)</span>':""}</span></div>`).join("")}
    ${d.sell_checks?`<div class="fl" style="font-size:13px;font-weight:600;margin:10px 0 4px">Sell warnings (${d.sell_checks.filter(c=>c.pass&&!c.skipped).length}/${d.sell_checks.filter(c=>!c.skipped).length})</div>
    ${d.sell_checks.map(c=>`<div class="chk"><b class="${c.skipped?"skip":c.pass?"no":"ok"}">${c.skipped?"–":c.pass?"!":"·"}</b><span>${c.label}</span></div>`).join("")}`:""}
    ${why(xLabel(d), "Why this label?")}</div>

  <div class="sec"><h3>Score breakdown</h3><div class="mute" style="margin-bottom:6px">Each part is a 0–100 rank vs the other ${d.market} stocks, weighted into the total.</div>
    ${d.parts.map(p=>`<div class="prow"><span>${p.label} <span class="mute">× ${Math.round(p.weight*100)}%</span></span><span class="v">${p.value}</span><i><span style="width:${p.value}%"></span></i></div>`).join("")}
    <div class="grid" style="margin-top:10px"><div class="kv"><small>Value vs sector</small><b>${d.sub.value}</b></div><div class="kv"><small>Quality</small><b>${d.sub.quality}</b></div><div class="kv"><small>Growth</small><b>${d.sub.growth}</b></div><div class="kv"><small>Financial health</small><b>${d.sub.health??"–"}</b></div><div class="kv"><small>Analysts</small><b>${d.analyst.rating?esc(d.analyst.rating).replace("_"," "):"–"}</b></div></div>
    ${up!=null?`<div class="mute" style="margin-top:8px">Average analyst target ${d.analyst.target} (${pct(up)} from here).</div>`:""}
    ${why(xScore(d, up))}</div>

  <div class="sec"><h3>Price chart</h3><div class="rng" id="rng"></div><div id="chart"></div><div id="tip"></div>
    <div class="legend"><span style="--c:var(--acc)">Price</span><span style="--c:var(--ma50)">50-day avg</span><span style="--c:var(--ma200)">200-day avg</span><span style="--c:var(--idx)">Index (scaled)</span></div>
    ${why(xChart(d, base))}</div>

  <div class="sec"><h3>Technicals</h3><div class="grid">${Object.entries(d.tech).map(([k,v])=>{
      const isPct = !/RSI|Volume/.test(k), s = v==null?"–": /Volatility/.test(k)? (v*100).toFixed(1)+"%" : isPct? pct(v) : (k.startsWith("Volume")? v.toFixed(2)+"x" : v);
      const cls = v==null?"": k.startsWith("RSI") ? (v>70?"bad":v<30?"good":"") : isPct && !/Volatility/.test(k) ? (v>0?"good":"bad") : "";
      return `<div class="kv"><small>${k}</small><b class="${cls}">${s}</b></div>`}).join("")}</div>
    ${why(xTech(d))}</div>

  <div class="sec"><h3>Fundamentals vs sector</h3><table><tr><th>Metric</th><th>${tk(d.ticker)}</th><th>Sector median</th></tr>
    ${d.fund.map(f=>{ let cls=""; if(f.value!=null&&f.sector!=null){ const better = f.better==="high" ? f.value>f.sector : f.value<f.sector; cls = better?"good":"bad"; }
      return `<tr><td>${f.label}</td><td class="${cls}">${fmtF(f.value,f.kind)}</td><td>${fmtF(f.sector,f.kind)}</td></tr>`}).join("")}</table>
    <div class="mute" style="margin-top:6px">Green = better than the typical company in its sector.</div>
    ${why(xFund(d))}</div>

  ${healthSection(d)}

  <div class="sec"><h3>News (last 10 days)</h3>
    ${d.events&&d.events.length?`<div class="chips" style="margin:0 0 8px">${d.events.map(e=>`<span class="chip ${e.impact<0?"bad":""}">${e.impact>0?"▲":e.impact<0?"▼":"•"} ${esc(e.label)}</span>`).join("")}</div>`:""}
    <div class="mute" style="margin-bottom:6px">Recency-weighted sentiment: <b style="color:${sentColor(d.news_avg)}">${d.news_avg??0}</b> · competitors: <b style="color:${sentColor(d.peer_avg)}">${d.peer_avg??0}</b>${d.macro_share>0?` · ${Math.round(d.macro_share*100)}% about policy/macro`:""}</div>
    ${d.news.length ? d.news.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}
      <div class="mute">${esc(n.publisher||"")}${n.quality==="promo"?" (promotional, half weight)":""} ${n.date||""}${n.macro?" · policy/macro":""}${(n.events||[]).map(e=>` · <b style="color:${BAD.includes(e)?"var(--neg)":"var(--acc)"}">${esc(e)}</b>`).join("")}</div></div>`).join("") : `<div class="mute">No recent headlines.</div>`}
    ${why(xNews(d))}</div>

  <div class="sec"><h3>Sector &amp; politics</h3>
    <div class="grid"><div class="kv"><small>Macro score (−1 to 1)</small><b class="${d.macro.score>0.05?"good":d.macro.score<-0.05?"bad":""}">${d.macro.score>0?"+":""}${d.macro.score}</b></div>
    <div class="kv"><small>${esc(d.sector)} news mood</small><b class="${d.macro.sector_news>0.05?"good":d.macro.sector_news<-0.05?"bad":""}">${d.macro.sector_news>0?"+":""}${d.macro.sector_news}</b></div></div>
    ${d.macro.sector_why?`<div class="mute" style="margin-top:8px">${esc(d.macro.sector_why)}</div>`:""}
    ${d.macro.effects.length?`<div style="margin-top:10px;font-size:14px">${d.macro.effects.map(e=>`<div class="chk"><b class="${e.effect>0?"ok":"no"}">${e.effect>0?"▲":"▼"}</b><span>${esc(e.theme)} <span class="mute">(${e.effect>0?"+":""}${e.effect})</span></span></div>`).join("")}</div>`:`<div class="mute" style="margin-top:8px">No political or macro theme is notably affecting this stock right now.</div>`}
    ${d.macro.sector_headlines.length?`<div class="mute" style="margin:8px 0 2px">Sector headlines:</div>`+d.macro.sector_headlines.map(n=>`<div class="news"><span class="dot" style="background:${sentColor(n.score)}"></span>${n.link?`<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>`:esc(n.title)}<div class="mute">${esc(n.publisher||"")} ${n.date||""}</div></div>`).join(""):""}
    ${why(xMacro(d))}</div>

  <div class="sec"><h3>Peers in ${esc(d.sector)}</h3>
    ${d.peers.length ? d.peers.map(p=>`<div class="peer" onclick="openStock('${p.ticker}')"><span><b>${tk(p.ticker)}</b>${p.signal?`<span class="sig ${p.signal}">${p.signal}</span>`:""}<div class="mute">${esc(p.name)}</div></span>
      <span style="text-align:right"><b>${p.score}</b><div class="mute">3m ${pct(p.ret3m,0)} · P/E ${p.pe??"–"} · news <span style="color:${sentColor(p.news)}">${p.news??0}</span></div></span></div>`).join("") : `<div class="mute">No peers in the screened list.</div>`}
    ${why(xPeers(d))}</div>
  <footer>Not financial advice. Data from Yahoo Finance; may be delayed or incomplete.</footer>`;
  drawChart(d, base, 252);
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
  return `<p><b>${esc(d.name)}</b> scores <b>${d.score}</b> out of 100, which puts it at <b>#${d.rank} of ${d.of}</b> ${d.market} stocks — better than about ${top}% of them.
    Its strongest area is <b>${parts[0].label.toLowerCase()}</b> (${parts[0].value}/100) and its weakest is <b>${parts[parts.length-1].label.toLowerCase()}</b> (${parts[parts.length-1].value}/100).
    The label is <b>${d.signal||"HOLD"}</b>: ${LABEL_INFO[d.signal||"HOLD"]}.${(d.flags||[]).includes("REBOUND")?" It's also flagged <b>REBOUND</b>: a decent company whose price has fallen hard recently, which sometimes bounces back.":""}${(d.flags||[]).includes("TAKE PROFIT")?" It's flagged <b>TAKE PROFIT</b>: it has risen a lot very quickly and the support behind the move is fading.":""}</p>`;
}
function xLabel(d){
  const failB = d.checks.filter(c=>!c.pass&&!c.skipped).map(c=>c.label.toLowerCase());
  const passS = (d.sell_checks||[]).filter(c=>c.pass&&!c.skipped).map(c=>c.label.toLowerCase());
  const sg = d.signal||"HOLD";
  let t = "";
  if (sg==="BUY") t = "Every buy check passes: it's highly ranked, the price is trending up without being overheated, the business looks solid compared with similar companies, and the news backdrop isn't hurting it.";
  else if (sg==="WATCH") t = `It passes every buy check except one: <b>${failB.join(", ")}</b>. If that changes, it would become a BUY.`;
  else if (sg==="SELL") t = "It fails on every front at once — low ranking, falling price, weak business numbers, negative news and a negative price model. If you own it, the screener suggests getting out.";
  else if (sg==="AVOID") t = (d.red_flags||[]).length ? `There's recent serious bad news: <b>${d.red_flags.map(esc).join(", ")}</b>. Stocks often keep falling for a while after news like this, so it's safer to wait.` : "It's near the bottom of the rankings and its business numbers are weak compared with its sector. Not a good time to buy.";
  else t = `Nothing stands out. It fails ${failB.length} buy check${failB.length===1?"":"s"}${failB.length?` (${failB.slice(0,3).join(", ")}${failB.length>3?"…":""})`:""} and shows ${passS.length} of ${(d.sell_checks||[]).length} sell warnings.`;
  return `<p>${t}</p><p class="mute">✓ = passes, ✗ = fails, ! = warning present, – = not used in this market.</p>`;
}
function xScore(d, up){
  const L = d.parts.map(p=>`<li><b>${p.label}</b> ${p.value}/100 — ${rankWord(p.value)}.</li>`).join("");
  const v = d.sub;
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
function closeSheet(){ $("sheet").classList.remove("open"); document.body.style.overflow=""; }
window.addEventListener("popstate", e => { if (e.state && e.state.t) openStock(e.state.t, false); else closeSheet(); });
if (location.hash.length > 1) { history.replaceState(null, "", location.pathname); openStock(decodeURIComponent(location.hash.slice(1))); }
render();
</script></body></html>"""


def write_page(payload, path):
    from events import BAD
    page = PAGE.replace("__BAD_EVENTS__", ",".join(json.dumps(b) for b in sorted(BAD)))
    with open(path, "w") as f:
        f.write(page.replace("__DATA__", json.dumps(payload, default=str, separators=(",", ":"))))
