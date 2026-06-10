"""
============================================================================
 BUILD_ARTIFACT  --  systemic_model
============================================================================
 Emits tier_artifact.html: the COMBINED, INTERACTIVE dashboard for Cowork —
 recovery-profile bars + a sortable numbers table (Grid.js) + an "Ask Claude"
 box that answers questions about the data in-page (window.cowork.askClaude).

 Generated from the latest results.json + drift_history.json, so re-running it
 (then update_artifact) keeps the sidebar page current. Light-mode, fully
 self-contained except the two allowed Grid.js CDN tags.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

import tiering as T
import build_dashboard as B

OUT = os.path.join(HERE, "tier_artifact.html")
GRID_JS = ('<script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" '
           'integrity="sha384-/XXDzxe4FsGiAe50i/u9pY/Vy/uX654MHB1xoc1BJNnH1WXHhqHga9g3q5tF4gj7" '
           'crossorigin="anonymous"></script>')
GRID_CSS = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" '
            'integrity="sha384-jZvDSsmGB9oGGT/4l9bHXGoAv1OxvG/cFmSo0dZaSqmBgvQTKDBFAMftlXTmMbNW" '
            'crossorigin="anonymous">')
CHART_JS = ('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" '
            'integrity="sha384-iU8HYtnGQ8Cy4zl7gbNMOhsDTTKX02BTXptVP/vqAWIaTfM7isw76iyZCsjL2eVi" '
            'crossorigin="anonymous"></script>')


def _rows(res, deltas):
    out = []
    metrics = {r["name"]: r for r in T.build_rows(res)}   # vs_sp, vs_schd, perm_vs_sp, true_perm
    for name, (kind, theme, g) in T.UNIVERSE.items():
        c = res["companies"]["recovery_cond"].get(name)
        if not c:
            continue
        pdd = c.get("p_dd25") or 0.0
        p12, p24, p36 = B._curve(res, name, 12), B._curve(res, name, 24), B._curve(res, name, 36)
        b = B._buckets(res, name)
        d30 = deltas.get(name, (None, None))[1]
        m = metrics.get(name, {})
        tier = ("Trading" if name in T.LEVERAGED else
                "High" if g > 0.40 else ("Moderate" if g >= 0.15 else "Safe"))
        out.append(dict(name=name, kind=kind, theme=theme, tier=tier, g=g, pdd=pdd,
                        p12=p12, p24=p24, p36=p36, tail=b["gt3"],
                        buckets=[b["no_fall"], b["le1"], b["y12"], b["y23"], b["gt3"]],
                        true_perm=m.get("true_perm"), perm_vs_sp=m.get("perm_vs_sp"),
                        vs_sp=m.get("vs_sp"), vs_schd=m.get("vs_schd"), d30=d30))
    return out


def build(kind=None, cap=None, out_path=None, title_suffix=""):
    res = B._load(B.RESULTS)
    if not res:
        print("No results.json — run the model first.")
        return None
    out_path = out_path or OUT
    hist = B._load(B.HISTORY, {"history": []})
    deltas, _, _ = B._deltas(hist)
    rows = _rows(res, deltas)
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    if cap:  # keep top `cap` by growth WITHIN each final tier; Trading kept whole
        kept = []
        for tier in ("High", "Moderate", "Safe"):
            grp = sorted([r for r in rows if r["tier"] == tier], key=lambda r: -r["g"])[:cap]
            kept += grp
        kept += [r for r in rows if r["tier"] == "Trading"]   # never capped away
        rows = kept
    as_of = res.get("as_of", "?")

    banners = ""
    try:
        import macro_stress as _MS
        st = _MS.compute(res.get("macro", {})) if res.get("macro") else None
        if st:
            banners += (f'<div style="background:#f1efe8;border-radius:10px;padding:8px 13px;margin-bottom:10px;font-size:12px;color:#5f5e5a">'
                        f'<b>Macro-stress {round(st["score"]*100)}/100</b> ({_MS.stress_label(st["score"])}) — '
                        f'structural {round(st["structural"]*100)}, acute {round(st["acute"]*100)}; scales drawdown odds x{_MS.crisis_mult(st["score"]):.2f}.</div>')
    except Exception:
        pass
    try:
        cr = B._load(os.path.join(HERE, "correlation_report.json"))
        if cr and cr.get("baskets"):
            u = next((b for b in cr["baskets"] if "universe" in b["label"].lower()), cr["baskets"][0])
            banners += (f'<div style="background:#fceBEB;border-radius:10px;padding:8px 13px;margin-bottom:14px;font-size:12px;color:#a32d2d">'
                        f'<b>Concentration</b> — ~{u["neff_with"]:.0f} effective bets across {u["n"]} names (corr {u["rho_with"]:.2f}); '
                        f'a specialized ETF ≈ 0.95 correlated with its lead holding. P(equal-weight basket &gt;25% in 18m) ≈ {u["port_dd25_with"]*100:.0f}%. '
                        f'This list is mostly one bet — size accordingly.</div>')
    except Exception:
        pass

    # ---- server-rendered recovery bars, grouped by tier ----
    COL = ["transparent", "#1d9e75", "#9fe1cb", "#ef9f27", "#e24b4a"]
    tier_defs = [("Tier 1 · High growth", "> 40%", lambda r: r["tier"] == "High"),
                 ("Tier 2 · Moderate growth", "15–40%", lambda r: r["tier"] == "Moderate"),
                 ("Tier 3 · Safe / smaller growth", "< 15%", lambda r: r["tier"] == "Safe"),
                 ("Trading vehicles · 3x leveraged", "volatility decay — excluded from tiers",
                  lambda r: r["tier"] == "Trading")]
    bar_sections = []
    for label, sub, test in tier_defs:
        mem = [r for r in rows if test(r)]
        cards = []
        for r in mem:
            gw = round(min(r["g"] / 0.80, 1.0) * 100)
            segs = "".join(f'<span style="width:{round(v*100,1)}%;background:{COL[i]}"></span>'
                           for i, v in enumerate(r["buckets"]))
            tcls = "lo" if r["tail"] <= 0.22 else ("mid" if r["tail"] <= 0.26 else "hi")
            badge = "etf" if r["kind"] == "ETF" else "stk"
            cards.append(
                f'<div class="row"><div class="nm">{r["name"]}'
                f'<span class="bd {badge}">{r["kind"]}</span></div>'
                f'<div class="gw"><div class="gbar"><i style="width:{gw}%"></i></div>'
                f'<b>{round(r["g"]*100)}%</b></div>'
                f'<div class="rec">{segs}</div>'
                f'<div class="tl {tcls}">{round(r["tail"]*100)}%</div></div>')
        bar_sections.append(
            f'<div class="tierhead">{label} <span class="sub">{sub} · {len(mem)} names</span></div>'
            f'<div class="tier">{"".join(cards)}</div>')
    bars_html = "".join(bar_sections)

    data_json = json.dumps([
        dict(name=r["name"], type=r["kind"], theme=r["theme"], tier=r["tier"],
             growth=round(r["g"]*100), pfall=round(r["pdd"]*100),
             r1=round(r["p12"]*100), r2=round(r["p24"]*100), r3=round(r["p36"]*100),
             tail=round(r["tail"]*100), buckets=[round(x*100, 1) for x in r["buckets"]],
             xsp=(round(r["perm_vs_sp"], 1) if r.get("perm_vs_sp") else None),
             vssp=(round(r["vs_sp"], 2) if r.get("vs_sp") else None),
             vsschd=(round(r["vs_schd"], 2) if r.get("vs_schd") else None),
             d30=(round(r["d30"]*100) if r["d30"] is not None else None))
        for r in rows])
    show_toggle = kind is None

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Systemic + TAM dashboard</title>
{GRID_CSS}
<style>
:root{{color-scheme:light}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
background:#faf9f5;color:#1c1c1a;margin:0;padding:22px;line-height:1.5}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{font-size:21px;margin:0 0 2px}} .meta{{color:#6b6a64;font-size:13px;margin-bottom:16px}}
.explain{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:18px}}
.explain .b{{background:#fff;border:1px solid #e7e5dd;border-radius:10px;padding:11px 14px}}
.explain h4{{margin:0 0 3px;font-size:13px}} .explain p{{margin:0;font-size:12px;color:#6b6a64}}
.legend{{display:flex;flex-wrap:wrap;gap:12px;font-size:11px;color:#6b6a64;margin-bottom:14px}}
.legend i{{display:inline-block;width:13px;height:9px;vertical-align:middle;margin-right:3px;border:0.5px solid #ddd}}
.tierhead{{font-size:15px;font-weight:600;margin:18px 0 6px}} .sub{{color:#8b8a82;font-weight:400;font-size:12px}}
.tier{{border:1px solid #e7e5dd;border-radius:10px;overflow:hidden;background:#fff}}
.row{{display:grid;grid-template-columns:150px 90px 1fr 48px;align-items:center;gap:10px;
padding:6px 13px;border-bottom:1px solid #f0eee7;font-size:13px}} .row:last-child{{border-bottom:none}}
.nm{{font-weight:600}} .bd{{font-size:9px;padding:1px 4px;border-radius:4px;margin-left:5px}}
.bd.etf{{background:#f1efe8;color:#5f5e5a}} .bd.stk{{background:#e6f1fb;color:#185fa5}}
.gw{{display:flex;align-items:center;gap:6px}} .gbar{{flex:1;height:7px;background:#efeee8;border-radius:4px;overflow:hidden}}
.gbar i{{display:block;height:100%;background:#185fa5}} .gw b{{font-size:12px;min-width:28px}}
.rec{{display:flex;height:11px;border-radius:3px;overflow:hidden;background:#efeee8;border:0.5px solid #e7e5dd}}
.rec span{{height:100%}}
.tl{{text-align:center;font-weight:600;font-size:12px;padding:2px 0;border-radius:6px}}
.tl.lo{{background:#e1f5ee;color:#0f6e56}} .tl.mid{{background:#faeeda;color:#854f0b}} .tl.hi{{background:#fceBEB;color:#a32d2d}}
h2{{font-size:16px;margin:24px 0 8px}}
#tbl{{font-size:12px}}
.ask{{margin-top:22px;background:#fff;border:1px solid #e7e5dd;border-radius:12px;padding:14px 16px}}
.chips{{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0}}
.chip{{font-size:12px;border:1px solid #d8d6cd;background:#faf9f5;border-radius:16px;padding:4px 11px;cursor:pointer}}
.chip:hover{{background:#f0eee7}}
#q{{width:100%;min-height:46px;border:1px solid #d8d6cd;border-radius:8px;padding:8px;font:inherit;font-size:13px;box-sizing:border-box}}
#go{{margin-top:8px;border:1px solid #185fa5;background:#185fa5;color:#fff;border-radius:8px;padding:7px 16px;cursor:pointer;font-size:13px}}
#ans{{margin-top:12px;font-size:13px;white-space:pre-wrap;color:#1c1c1a;min-height:8px}}
.foot{{color:#8b8a82;font-size:11px;margin-top:20px}}
.toggle{{display:inline-flex;border:1px solid #d8d6cd;border-radius:8px;overflow:hidden;margin-bottom:12px}}
.toggle button{{border:0;background:#fff;color:#5f5e5a;padding:6px 16px;cursor:pointer;font:inherit;font-size:13px;border-right:1px solid #e7e5dd}}
.toggle button:last-child{{border-right:0}} .toggle button.on{{background:#185fa5;color:#fff;font-weight:500}}
.charts{{background:#fff;border:1px solid #e7e5dd;border-radius:12px;padding:14px 16px;margin:6px 0 8px}}
.cbar{{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-bottom:10px}}
.cbar .clab{{font-size:12px;color:#6b6a64;margin-right:2px}}
.cbar button{{font-size:12px;border:1px solid #d8d6cd;background:#faf9f5;border-radius:8px;padding:5px 11px;cursor:pointer}}
.cbar button.con{{background:#185fa5;color:#fff;border-color:#185fa5;font-weight:500}}
.cbar select{{font-size:12px;border:1px solid #d8d6cd;border-radius:8px;padding:5px 8px;background:#fff}}
</style></head><body><div class="wrap">
<h1>Systemic + TAM — growth × recovery, with change tracking{title_suffix}</h1>
<div class="meta">Model as of {as_of} · research model, not investment advice</div>
{banners}

<div class="explain">
  <div class="b"><h4>Growth % — how fast</h4><p>Forward 18-month revenue-growth estimate; sets the tier (&gt;40% / 15–40% / &lt;15%).</p></div>
  <div class="b"><h4>Recovery bar &amp; &gt;3y % — how long back</h4><p>Grey = never fell &gt;25%. Greens = a deep fall back within 1/2/3y. Red = &gt;3y (long &amp; uncertain — execution risk for a single stock; an ETF dilutes it).</p></div>
</div>

<div class="legend">
  <span><i style="background:#185fa5"></i>growth 18m</span>
  <span><i style="background:#efeee8"></i>no &gt;25% fall</span>
  <span><i style="background:#1d9e75"></i>back ≤1y</span>
  <span><i style="background:#9fe1cb"></i>1–2y</span>
  <span><i style="background:#ef9f27"></i>2–3y</span>
  <span><i style="background:#e24b4a"></i>&gt;3y</span>
</div>

{'<div class="toggle" id="toggle"><button data-k="all" class="on">All</button><button data-k="stock">Stocks</button><button data-k="ETF">ETFs</button></div>' if show_toggle else ''}
<div class="charts">
  <div class="cbar">
    <span class="clab">Chart:</span>
    <button data-c="scatter" class="con">Growth vs risk</button>
    <button data-c="bar">Ranking</button>
    <button data-c="pie">By sector</button>
    <button data-c="recovery">Recovery curve</button>
    <select id="metric" style="display:none">
      <option value="tail">&gt;3y tail (risk)</option>
      <option value="growth">growth</option>
      <option value="pfall">P(&gt;25% fall)</option>
    </select>
  </div>
  <div style="position:relative;height:340px;"><canvas id="chart" role="img" aria-label="Selected chart of the universe"></canvas></div>
</div>

<div id="bars"></div>

<h2>All numbers <span class="sub">— click a column header to sort</span></h2>
<div id="tbl"></div>

<div class="ask">
  <div style="font-size:14px;font-weight:600;">Ask about this dashboard</div>
  <div class="sub">Answered in-page from the data below. Click a starter or type your own.</div>
  <div class="chips" id="chips"></div>
  <textarea id="q" placeholder="e.g. Why is CoreWeave's >3y tail so high if it grows fast?"></textarea>
  <button id="go">Ask</button>
  <div id="ans"></div>
</div>

<div class="foot">The recovery bar &amp; &gt;3y tail are unconditional (across all scenarios), comparable across names and between stocks &amp; ETFs.
Conditional recover-by-1/2/3y columns answer "if it falls &gt;25%, odds it's back by then". Regenerated each run.</div>
</div>
{GRID_JS}
{CHART_JS}
<script>
const DATA = {data_json};
let FILTER='all';
const COL=['transparent','#1d9e75','#9fe1cb','#ef9f27','#e24b4a'];
const TIERS=[['Tier 1 · High growth','> 40%',d=>d.growth>40],
             ['Tier 2 · Moderate growth','15–40%',d=>d.growth>=15&&d.growth<=40],
             ['Tier 3 · Safe / smaller growth','< 15%',d=>d.growth<15]];
function shown(){{return FILTER==='all'?DATA:DATA.filter(d=>d.type===FILTER);}}
function renderBars(){{
  const host=document.getElementById('bars'); host.innerHTML='';
  const rows=shown();
  TIERS.forEach(([label,sub,test])=>{{
    const mem=rows.filter(test).sort((a,b)=>b.growth-a.growth);
    if(!mem.length)return;
    const sec=document.createElement('div'); sec.style.marginBottom='6px';
    sec.innerHTML=`<div class="tierhead">${{label}} <span class="sub">${{sub}} · ${{mem.length}} ${{FILTER==='ETF'?'ETFs':'names'}}</span></div>`;
    const tier=document.createElement('div'); tier.className='tier';
    mem.forEach(d=>{{
      const gw=Math.round(Math.min(d.growth/80,1)*100);
      const segs=d.buckets.map((v,i)=>`<span style="width:${{v}}%;background:${{COL[i]}}"></span>`).join('');
      const tcls=d.tail<=22?'lo':(d.tail<=26?'mid':'hi');
      const bd=d.type==='ETF'?'etf':'stk';
      const r=document.createElement('div'); r.className='row';
      r.innerHTML=`<div class="nm">${{d.name}}<span class="bd ${{bd}}">${{d.type}}</span></div>
        <div class="gw"><div class="gbar"><i style="width:${{gw}}%"></i></div><b>${{d.growth}}%</b></div>
        <div class="rec">${{segs}}</div><div class="tl ${{tcls}}">${{d.tail}}%</div>`;
      tier.appendChild(r);
    }});
    sec.appendChild(tier); host.appendChild(sec);
  }});
}}
function tailFmt(c){{const v=c;const col=v<=22?['#e1f5ee','#0f6e56']:(v<=26?['#faeeda','#854f0b']:['#fceBEB','#a32d2d']);
  return gridjs.html(`<span style="background:${{col[0]}};color:${{col[1]}};font-weight:600;padding:2px 7px;border-radius:6px">${{v}}%</span>`);}}
function dFmt(v){{if(v===null)return gridjs.html('<span style="color:#8b8a82">new</span>');
  if(v>=1)return gridjs.html(`<span style="color:#a32d2d">▲+${{v}}</span>`);
  if(v<=-1)return gridjs.html(`<span style="color:#0f6e56">▼${{v}}</span>`);
  return gridjs.html('<span style="color:#8b8a82">0</span>');}}
let grid=null;
function renderGrid(){{
  if(typeof gridjs==='undefined')return;   // table lib not ready yet
  const rows=shown().map(r=>[r.name,r.type,r.tier,r.growth,r.pfall,r.r2,r.tail,r.xsp,r.vssp,r.vsschd,r.d30]);
  const vsFmt=v=>{{if(v===null||v===undefined)return gridjs.html('<span style="color:#8b8a82">—</span>');
    const col=v>=1?['#e1f5ee','#0f6e56']:(v>=0.7?['#faeeda','#854f0b']:['#fceBEB','#a32d2d']);
    return gridjs.html(`<span style="background:${{col[0]}};color:${{col[1]}};font-weight:600;padding:2px 6px;border-radius:6px">${{v}}</span>`);}};
  const cfg={{columns:[{{name:'Name'}},{{name:'Type'}},{{name:'Tier'}},
      {{name:'Growth',formatter:c=>c+'%'}},{{name:'P(>25% fall)',formatter:c=>c+'%'}},
      {{name:'↻2y',formatter:c=>c+'%'}},{{name:'>3y tail',formatter:c=>tailFmt(c)}},
      {{name:'×S&P',formatter:c=>(c===null?'—':c+'×')}},
      {{name:'vs S&P',formatter:c=>vsFmt(c)}},{{name:'vs SCHD',formatter:c=>vsFmt(c)}},
      {{name:'Δ30d',formatter:c=>dFmt(c)}}],
    data:rows, sort:true, search:true, pagination:{{limit:12}}}};
  if(grid){{grid.updateConfig(cfg).forceRender();}}
  else{{grid=new gridjs.Grid(cfg); grid.render(document.getElementById('tbl'));}}
}}
// ---- Chart.js visuals (selectable) ----
let CHART='scatter', chartObj=null;
const PAL=['#185fa5','#1d9e75','#ef9f27','#e24b4a','#7f77dd','#d4537e','#d85a30','#888780','#5dcaa5','#85b7eb','#97c459','#f0997b','#afa9ec','#b4b2a9'];
function tierColor(t){{return t==='High'?'#e24b4a':(t==='Moderate'?'#ef9f27':'#1d9e75');}}
function renderChart(){{
  if(typeof Chart==='undefined')return;
  const rows=shown(); const ctx=document.getElementById('chart');
  document.getElementById('metric').style.display = (CHART==='bar')?'inline-block':'none';
  if(chartObj){{chartObj.destroy(); chartObj=null;}}
  let cfg;
  if(CHART==='scatter'){{
    cfg={{type:'scatter',data:{{datasets:[{{
        data:rows.map(r=>({{x:r.growth,y:r.tail,nm:r.name}})),
        backgroundColor:rows.map(r=>tierColor(r.tier)),pointRadius:6,pointHoverRadius:8}}]}},
      options:{{responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>c.raw.nm+': growth '+c.raw.x+'%, >3y tail '+c.raw.y+'%'}}}}}},
        scales:{{x:{{title:{{display:true,text:'expected 18m growth %'}}}},
                 y:{{title:{{display:true,text:'>3y tail % — risk (lower safer)'}}}}}}}}}};
  }} else if(CHART==='bar'){{
    const m=document.getElementById('metric').value;
    const srt=[...rows].sort((a,b)=>b[m]-a[m]).slice(0,16);
    cfg={{type:'bar',data:{{labels:srt.map(r=>r.name),datasets:[{{
        data:srt.map(r=>r[m]),backgroundColor:srt.map(r=>tierColor(r.tier))}}]}},
      options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>c.parsed.x+'%'}}}}}},
        scales:{{x:{{ticks:{{callback:v=>v+'%'}}}}}}}}}};
  }} else if(CHART==='pie'){{
    const counts={{}}; rows.forEach(r=>counts[r.theme]=(counts[r.theme]||0)+1);
    const labels=Object.keys(counts);
    cfg={{type:'doughnut',data:{{labels,datasets:[{{data:labels.map(l=>counts[l]),
        backgroundColor:labels.map((l,i)=>PAL[i%PAL.length])}}]}},
      options:{{responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{position:'right',labels:{{boxWidth:12,font:{{size:11}}}}}},
          tooltip:{{callbacks:{{label:c=>c.label+': '+c.parsed+' names'}}}}}}}}}};
  }} else {{ // recovery curve: avg recover-by 1/2/3y for the shown set, by tier
    const tiers=['High','Moderate','Safe'];
    const xs=['1y','2y','3y'];
    const ds=tiers.map(t=>{{
      const g=rows.filter(r=>r.tier===t);
      const avg=k=>g.length?Math.round(g.reduce((s,r)=>s+r[k],0)/g.length):null;
      return {{label:t+' tier',data:[avg('r1'),avg('r2'),avg('r3')],
        borderColor:tierColor(t),backgroundColor:tierColor(t),tension:.3,
        borderWidth:2,spanGaps:true}};
    }}).filter(d=>d.data.some(v=>v!==null));
    cfg={{type:'line',data:{{labels:xs,datasets:ds}},
      options:{{responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{position:'bottom'}},tooltip:{{callbacks:{{label:c=>c.dataset.label+': '+c.parsed.y+'% recovered'}}}}}},
        scales:{{y:{{title:{{display:true,text:'P(recovered | fell >25%)'}},ticks:{{callback:v=>v+'%'}}}}}}}}}};
  }}
  chartObj=new Chart(ctx,cfg);
}}
function safe(fn){{try{{fn();}}catch(e){{console.error(e);}}}}
function refresh(){{safe(renderBars); safe(renderGrid); safe(renderChart);}}
// Wire the controls FIRST, so selections always respond even if a chart
// library is still loading. Renders are guarded and re-run on window load.
const tg=document.getElementById('toggle');
if(tg){{tg.querySelectorAll('button').forEach(b=>b.onclick=()=>{{
  FILTER=b.dataset.k; tg.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b)); refresh();}});}}
const cbar=document.querySelector('.cbar');
if(cbar){{cbar.querySelectorAll('button').forEach(b=>b.onclick=()=>{{
  CHART=b.dataset.c; cbar.querySelectorAll('button').forEach(x=>x.classList.toggle('con',x===b)); safe(renderChart);}});}}
const met=document.getElementById('metric'); if(met){{met.onchange=()=>safe(renderChart);}}
refresh();
window.addEventListener('load', refresh);

const STARTERS=[
 "Which names have the best growth for the lowest >3y tail?",
 "Why is CoreWeave's >3y tail high if it grows fast?",
 "Compare the ETFs vs the single stocks on risk.",
 "What changed most over the last 30 days?",
 "If I can hold 3 years, which high-growth names look survivable?"];
const chips=document.getElementById('chips'), q=document.getElementById('q'),
      go=document.getElementById('go'), ans=document.getElementById('ans');
STARTERS.forEach(s=>{{const c=document.createElement('span');c.className='chip';c.textContent=s;
  c.onclick=()=>{{q.value=s;ask();}};chips.appendChild(c);}});
async function ask(){{
  const text=q.value.trim(); if(!text)return;
  if(!(window.cowork&&window.cowork.askClaude)){{ans.textContent='Open this in Cowork to use the Ask box.';return;}}
  ans.textContent='Thinking…';
  try{{
    const prompt="You are looking at a growth-vs-recovery dashboard. Each row: name, type, tier, growth=expected 18m revenue growth %, pfall=P(>25% drawdown), r1/r2/r3=chance of recovering within 1/2/3 years IF it falls, tail=unconditional chance a >25% fall takes >3 years to recover (lower=safer), d30=30-day change in that tail. Answer this question using ONLY the data, concisely, naming specific tickers and numbers: "+text;
    const a=await window.cowork.askClaude(prompt, DATA);
    ans.textContent=(typeof a==='string')?a:JSON.stringify(a);
  }}catch(e){{ans.textContent='Error: '+e;}}
}}
go.onclick=ask;
q.addEventListener('keydown',e=>{{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey))ask();}});
</script></body></html>"""

    with open(out_path, "w") as f:
        f.write(html)
    print(f"Wrote {os.path.basename(out_path)}  ({len(rows)} names).")
    return out_path


if __name__ == "__main__":
    build()  # full universe -> tier_artifact.html
    build(kind="ETF", cap=3, title_suffix=" · ETFs only",
          out_path=os.path.join(HERE, "tier_artifact_etf.html"))
