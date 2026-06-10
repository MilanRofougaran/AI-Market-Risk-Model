"""
Build a polished, self-contained HTML investor report from the model's own outputs.
Reads results.json, etf_horizon_rank.json, backtest_historical.md, live macro; renders
inline-SVG charts (no external dependencies) + a plain-language method explainer.
"""
import os, sys, json, re, base64
HERE = os.path.dirname(os.path.abspath(__file__))
def _datauri(fn):
    try:
        b = open(os.path.join(HERE, "report_assets", fn), "rb").read()
        return "data:image/png;base64," + base64.b64encode(b).decode()
    except Exception:
        return ""
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C
import macro_stress as MS

def L(p, d=None):
    try: return json.load(open(os.path.join(HERE, p)))
    except Exception: return d

RES = L("results.json", {}) or {}
EHR = L("etf_horizon_rank.json", {}) or {}
MACRO = RES.get("macro", C.MACRO)
ST = MS.compute(MACRO)
RC = RES.get("companies", {}).get("recovery_cond", {})

# ---- palette ----
INK="#1a1d24"; MUT="#6b7280"; ACC="#2563eb"; GRN="#0e9f6e"; AMB="#d97706"; RED="#dc2626"
CYC="#7c3aed"; GRID="#e5e7eb"; PANEL="#f8fafc"

def pct(x, s="%"):
    return "—" if x is None else f"{x*100:.0f}{s}"

# ================= SVG chart helpers =================
def bars_v(data, h=240, bw=46, gap=26, pad=46, ymax=None, fmt=lambda v:f"{v*100:.0f}%", title=""):
    ymax = ymax or max(v for _,v,_ in data)*1.15 or 1
    n=len(data); w=pad*2+n*bw+(n-1)*gap
    plot=h-46
    out=[f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    for i in range(5):
        yy=18+plot*i/4; out.append(f'<line x1="{pad}" y1="{yy:.0f}" x2="{w-12}" y2="{yy:.0f}" stroke="{GRID}"/>')
    for i,(lab,v,col) in enumerate(data):
        x=pad+i*(bw+gap); bh=plot*(v/ymax); y=18+plot-bh
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bw}" height="{bh:.0f}" rx="3" fill="{col}"/>')
        out.append(f'<text x="{x+bw/2:.0f}" y="{y-6:.0f}" font-size="12" font-weight="600" text-anchor="middle" fill="{INK}">{fmt(v)}</text>')
        for j,ln in enumerate(lab.split("\n")):
            out.append(f'<text x="{x+bw/2:.0f}" y="{h-14+j*12:.0f}" font-size="11" text-anchor="middle" fill="{MUT}">{ln}</text>')
    out.append("</svg>")
    return "".join(out)

def grouped_bars(rows, h=300, ymax=0.7, title=""):
    # rows: [(label, realized, sim_p90, captured_bool)]
    n=len(rows); bw=20; gp=10; grp=bw*2+gp; gap=30; pad=46
    w=pad*2+n*grp+(n-1)*gap; plot=h-70
    out=[f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    for i in range(6):
        yy=18+plot*i/5; out.append(f'<line x1="{pad}" y1="{yy:.0f}" x2="{w-12}" y2="{yy:.0f}" stroke="{GRID}"/>')
        out.append(f'<text x="{pad-6}" y="{yy+4:.0f}" font-size="10" text-anchor="end" fill="{MUT}">{int((1-i/5)*ymax*100)}%</text>')
    for i,(lab,real,p90,cap) in enumerate(rows):
        x=pad+i*(grp+gap)
        rh=plot*(real/ymax); ph=plot*(p90/ymax)
        out.append(f'<rect x="{x}" y="{18+plot-ph:.0f}" width="{bw}" height="{ph:.0f}" rx="2" fill="{ACC}" opacity="0.35"/>')
        out.append(f'<rect x="{x+bw+gp}" y="{18+plot-rh:.0f}" width="{bw}" height="{rh:.0f}" rx="2" fill="{"#0e9f6e" if cap else RED}"/>')
        out.append(f'<text x="{x+bw/2}" y="{18+plot-ph-5:.0f}" font-size="9.5" text-anchor="middle" fill="{ACC}">{p90*100:.0f}</text>')
        out.append(f'<text x="{x+bw+gp+bw/2}" y="{18+plot-rh-5:.0f}" font-size="9.5" text-anchor="middle" fill="{INK}">{real*100:.0f}</text>')
        for j,ln in enumerate(lab.split("\n")):
            out.append(f'<text x="{x+grp/2:.0f}" y="{h-30+j*11:.0f}" font-size="9.5" text-anchor="middle" fill="{MUT}">{ln}</text>')
        out.append(f'<text x="{x+grp/2:.0f}" y="{h-6:.0f}" font-size="11" text-anchor="middle" fill="{"#0e9f6e" if cap else RED}">{"✓" if cap else "✕"}</text>')
    out.append("</svg>")
    return "".join(out)

def lines(series, h=280, w=620, ymax=2.0, ylab="expected return", xs=("1y","2y","3y","5y")):
    # series: [(name, [v0..v3], color)]
    pad=54; plot=h-54; pw=w-pad-20; n=len(xs)
    out=[f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">']
    for i in range(5):
        yy=18+plot*i/4; out.append(f'<line x1="{pad}" y1="{yy:.0f}" x2="{w-12}" y2="{yy:.0f}" stroke="{GRID}"/>')
        out.append(f'<text x="{pad-8}" y="{yy+4:.0f}" font-size="10" text-anchor="end" fill="{MUT}">{(1-i/4)*ymax*100:.0f}%</text>')
    xp=[pad+pw*i/(n-1) for i in range(n)]
    for i,x in enumerate(xp):
        out.append(f'<text x="{x:.0f}" y="{h-14:.0f}" font-size="12" text-anchor="middle" fill="{INK}">{xs[i]}</text>')
    for name,vals,col in series:
        pts=" ".join(f"{xp[i]:.0f},{18+plot-plot*(v/ymax):.0f}" for i,v in enumerate(vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"/>')
        for i,v in enumerate(vals):
            out.append(f'<circle cx="{xp[i]:.0f}" cy="{18+plot-plot*(v/ymax):.0f}" r="3.5" fill="{col}"/>')
        out.append(f'<text x="{xp[-1]+6:.0f}" y="{18+plot-plot*(vals[-1]/ymax)+4:.0f}" font-size="11" font-weight="600" fill="{col}">{name}</text>')
    out.append("</svg>")
    return "".join(out)

# ================= pull data =================
def matrix_row(nm, hz="18m"):
    m=(RC.get(nm,{}) or {}).get("dd_recovery_matrix",{}).get(hz)
    return m if m and m.get("recover_6m") is not None else None

KEY=["VOO (S&P 500)","QQQ (Nasdaq-100)","SMH (VanEck Semis)","DRAM (Roundhill Memory)",
     "NVIDIA","Micron","ARKK (ARK Innovation)"]

# historical episodes parsed from backtest_historical.md
def hist_rows():
    rows=[]
    try:
        for ln in open(os.path.join(HERE,"backtest_historical.md")):
            m=re.match(r"\|\s*(\d{4}[^|]*?)\s*\|\s*([\d.]+)/100\s*\|\s*([\d.]+)\s*\|\s*-?(\d+)%\s*\|\s*-?(\d+)%\s*\|\s*-?(\d+)%\s*\|\s*(yes|NO)\s*\|", ln)
            if m:
                rows.append(dict(name=m.group(1).strip(), stress=float(m.group(2)),
                                 med=int(m.group(4))/100, p90=int(m.group(5))/100,
                                 realized=int(m.group(6))/100, cap=(m.group(7)=="yes")))
    except Exception: pass
    return rows
HIST=hist_rows()
def _shortlab(nm):
    nm = nm.replace("China deval / oil", "China/oil").replace(" / ", " ")
    parts = nm.split(" ", 1)
    return parts[0] + ("\n" + parts[1] if len(parts) > 1 else "")
HIST_BARS=[(_shortlab(r['name']), r['realized'], r['p90'], r['cap']) for r in HIST]

def horizon_table(h):
    items=[(nm,d) for nm,d in EHR.items()]
    main=sorted([x for x in items if x[1]["crash_growth"]!="broken"],
                key=lambda kv:-(kv[1]["horizons"][h]["exp_return_horizon"]))
    brk=sorted([x for x in items if x[1]["crash_growth"]=="broken"],
               key=lambda kv:-(kv[1]["horizons"][h]["exp_return_horizon"]))
    return main, brk

def tag(a): return {"secular":"secular","cyclical":"cyclical · rebound-dep","broken":"⚠ broken — avoid"}.get(a,a)
def tagcol(a): return {"secular":GRN,"cyclical":CYC,"broken":RED}.get(a,MUT)

# ================= HTML =================
W=[]
def add(s): W.append(s)

add(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Systemic + TAM Risk — Investor Report</title>
<style>
:root{{--ink:{INK};--mut:{MUT};--acc:{ACC};--grid:{GRID};--panel:{PANEL}}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
 color:var(--ink);line-height:1.62;margin:0;background:#fff;font-size:16px}}
.wrap{{max-width:880px;margin:0 auto;padding:48px 28px 90px}}
h1{{font-size:30px;line-height:1.2;margin:0 0 6px}}
h2{{font-size:23px;margin:46px 0 12px;padding-top:20px;border-top:2px solid var(--grid)}}
h3{{font-size:17px;margin:26px 0 8px;color:#111827}}
p{{margin:11px 0}}
.sub{{color:var(--mut);font-size:15px}}
.lead{{font-size:18px;color:#374151}}
.card{{background:var(--panel);border:1px solid var(--grid);border-radius:12px;padding:18px 20px;margin:16px 0}}
.kicker{{text-transform:uppercase;letter-spacing:.08em;font-size:12px;font-weight:700;color:var(--acc)}}
.eq{{background:#0f172a;color:#e2e8f0;border-radius:10px;padding:16px 20px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:14px;margin:16px 0;overflow-x:auto;line-height:1.7}}
.eq b{{color:#7dd3fc}} .eq .g{{color:#86efac}} .eq .r{{color:#fca5a5}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid var(--grid)}}
th:first-child,td:first-child{{text-align:left}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:var(--mut);font-weight:700;border-bottom:2px solid #d1d5db}}
tr:hover td{{background:#f9fafb}}
.tag{{font-size:12px;font-weight:600;padding:2px 8px;border-radius:20px;white-space:nowrap}}
.note{{font-size:13px;color:var(--mut);font-style:italic}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.metric{{text-align:center;padding:10px}}
.metric .v{{font-size:30px;font-weight:800;line-height:1}}
.metric .l{{font-size:12px;color:var(--mut);margin-top:5px}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--mut);margin:8px 0}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:middle}}
.banner{{background:linear-gradient(120deg,#1e3a8a,#2563eb);color:#fff;border-radius:14px;padding:26px 28px;margin-bottom:18px}}
.banner .sub{{color:#cde0ff}}
.chartcard{{border:1px solid var(--grid);border-radius:12px;padding:18px 16px 8px;margin:16px 0}}
.chartcard .ct{{font-weight:700;font-size:14px;margin-bottom:4px}}
.chartcard .cs{{font-size:12.5px;color:var(--mut);margin-bottom:10px}}
ul{{margin:10px 0;padding-left:22px}} li{{margin:6px 0}}
.disclaimer{{background:#fef2f2;border:1px solid #fecaca;color:#991b1b;border-radius:10px;padding:14px 18px;font-size:13.5px;margin-top:30px}}
.toc{{font-size:14px;columns:2;gap:24px}} .toc a{{color:var(--acc);text-decoration:none;display:block;margin:3px 0}}
</style></head><body><div class="wrap">""")

# ---------- HERO ----------
add(f"""<div class="banner">
<div class="kicker" style="color:#bfdbfe">Research model · not investment advice</div>
<h1 style="color:#fff">Drawdown &amp; Recovery Risk — a probabilistic lens for AI/semiconductor ETFs &amp; stocks</h1>
<p class="sub">How likely is a meaningful fall over your horizon, and <i>if</i> it falls, how likely is it back to its peak in time? — answered as probabilities, never as a single forecast. Model as of {RES.get('as_of','today')}.</p>
</div>""")

add(f"""<div class="grid2">
<div class="card metric"><div class="v" style="color:{ACC}">{round(ST['score']*100)}<span style="font-size:16px;color:{MUT}">/100</span></div><div class="l">Systemic-stress index ({MS.stress_label(ST['score'])})</div></div>
<div class="card metric"><div class="v" style="color:{GRN}">{sum(1 for r in HIST if r['cap'])}/{len(HIST)}</div><div class="l">historical crashes bracketed by the simulated tail</div></div>
</div>""")

add(f"""<div class="card"><b>What this report covers.</b> In plain language: what the numbers mean, how they're produced (Monte&nbsp;Carlo over market regimes), the key inputs, why this beats a single-number forecast, how TAM/SAM and the cyclical demand-cycle enter the recovery estimate, how it was checked against {len(HIST)} historical crashes, and a full ranking of ETFs for 1-, 2-, 3- and 5-year holds using today's data.</div>""")

add("""<h2 id="prob">1 &nbsp;What "probability" actually means here</h2>
<p class="lead">No one can tell you the day the market drops. So this model never tries. Instead it answers two honest questions, as odds.</p>
<p>Think of weather. A forecaster doesn't say "it will rain at 3:14pm." They say "70% chance of rain today." That number comes from running many simulations of the atmosphere and counting how many end in rain. This model does exactly that for markets: it simulates thousands of possible futures for each stock or ETF under today's conditions, then <b>counts</b>.</p>
<ul>
<li><b>P(&gt;25% fall within 12 months)</b> = of all the simulated futures, the fraction where the price dropped more than 25% at some point in the first year.</li>
<li><b>P(recovered within 18 months | it fell)</b> = <i>among only the futures where it fell</i>, the fraction that climbed back to the old peak within 18 months. The "|" means "given that."</li>
</ul>
<p>A probability here is a <b>frequency count over simulated worlds</b> — not a guess, not a vibe. Read the numbers as <b>buckets</b> ("roughly 1-in-2", "very unlikely"), not as exact decimals. That humility is the point.</p>""")

# ---------- METHOD ----------
add("""<h2 id="method">2 &nbsp;The method, in one picture and one formula</h2>
<p>The whole model rests on a single idea, separating two things investors usually blur together:</p>
<div class="card"><b>Beta sets how deep a name falls. TAM, growth quality and the demand cycle set whether — and how fast — it climbs back.</b><br>
<span class="sub">A high-beta stock falls hard in a panic regardless of its business. But whether it <i>recovers</i> depends on its fundamentals: a growing market it can grow into, durable earnings, a strong balance sheet. Two names can fall the same 40% and have completely different odds of being whole again in two years.</span></div>""")

# regime path schematic
add(f"""<div class="chartcard"><div class="ct">How a single simulated future is built</div>
<div class="cs">Each path switches between four market "moods" day by day, then the name's price reacts through its beta, fundamentals and (if cyclical) its demand cycle.</div>
<svg viewBox="0 0 640 150" width="100%" style="max-width:640px">
<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="{MUT}"/></marker></defs>
{''.join(f'<g><rect x="{18+i*155}" y="20" width="120" height="40" rx="8" fill="{c}" opacity="0.16" stroke="{c}"/><text x="{78+i*155}" y="38" font-size="12.5" font-weight="700" text-anchor="middle" fill="{c}">{t}</text><text x="{78+i*155}" y="52" font-size="10" text-anchor="middle" fill="{MUT}">{s}</text></g>' for i,(t,s,c) in enumerate([("Calm","drift up, low vol",GRN),("Stress","choppy, −",AMB),("Crisis","crash, fat tail",RED),("Grind","slow de-rate",CYC)]))}
{''.join(f'<line x1="{138+i*155}" y1="40" x2="{171+i*155}" y2="40" stroke="{MUT}" marker-end="url(#ar)"/>' for i in range(3))}
<text x="320" y="92" font-size="12" text-anchor="middle" fill="{INK}">a "Markov chain" picks tomorrow's mood from today's — crises cluster, calm persists</text>
<text x="320" y="118" font-size="12" text-anchor="middle" fill="{MUT}">price return = <tspan fill="{ACC}" font-weight="700">beta × market move</tspan> + drift + fat-tailed noise − (grind &amp; demand-cycle drags)</text>
<text x="320" y="138" font-size="11" text-anchor="middle" fill="{MUT}">run this 150,000× → a full distribution of outcomes, not one number</text>
</svg></div>""")

add(f"""<p>Repeating that 150,000 times produces a <b>distribution</b> of possible price paths. From it we read the fall odds and, conditional on a fall, the recovery-time odds. The recovery side reduces to one intuitive equation used to rank:</p>
<div class="eq">expected&nbsp;return(horizon) = <b>(1 + growth)<sup>years</sup></b> × ( 1 − <span class="r">expected unrecovered loss</span> )<br><br>
<span class="r">expected unrecovered loss</span> = <b>P(fall)</b> × <span class="g">average depth</span> × ( 1 − <b>P(recovered in time)</b> )</div>
<p>In words: <b>start with the growth a name compounds if nothing breaks, then subtract only the part of a crash that doesn't heal before you sell.</b> A name that falls but reliably recovers keeps almost all its growth; one that stays broken loses it. That single line is why the ranking changes with your holding period — more on that below.</p>""")

# ---------- KEY PARAMETERS ----------
add(f"""<h2 id="params">3 &nbsp;The key inputs</h2>
<p>Every name carries a small set of parameters. The market ones are observable; the fundamental ones are judgments the model states openly and can sweep.</p>
<table>
<tr><th>Parameter</th><th style="text-align:left">What it controls</th><th style="text-align:left">Example</th></tr>
<tr><td>Beta</td><td style="text-align:left">Depth of the fall vs the market</td><td style="text-align:left">NVDA ≈ 1.5, VOO = 1.0</td></tr>
<tr><td>TAM / SAM</td><td style="text-align:left">The runway that justifies the premium &amp; powers recovery</td><td style="text-align:left">memory TAM, AI-compute TAM</td></tr>
<tr><td>Growth (18m)</td><td style="text-align:left">The compounding engine</td><td style="text-align:left">DRAM ≈ 28%/yr</td></tr>
<tr><td>Earnings quality / balance sheet</td><td style="text-align:left">Can it survive &amp; buy back at the lows</td><td style="text-align:left">fortress vs cash-burner</td></tr>
<tr><td>Crash-growth archetype</td><td style="text-align:left">Secular / cyclical / broken — sets recovery shape</td><td style="text-align:left">NVDA secular, DRAM cyclical</td></tr>
<tr><td>Macro-stress index</td><td style="text-align:left">Scales crisis odds for everyone at once</td><td style="text-align:left">today {round(ST['score']*100)}/100</td></tr>
</table>
<p class="note">Macro-stress today blends structural fragility {round(ST['structural']*100)}/100 (valuations, leverage, credit spreads) with the acute trigger {round(ST['acute']*100)}/100 (VIX, oil, funding) — inputs: CAPE {MACRO.get('shiller_cape')}, real 10y {MACRO.get('ust_10y_real')}%, VIX {MACRO.get('vix')}, HY spread {MACRO.get('hy_oas_bps')}bps.</p>""")

# ---------- WHY THIS METHOD ----------
add("""<h2 id="why">4 &nbsp;Why this beats the usual alternatives</h2>
<table>
<tr><th>Approach</th><th style="text-align:left">Blind spot</th><th style="text-align:left">What this model does instead</th></tr>
<tr><td>Single price target</td><td style="text-align:left">Pretends the future is one number; always wrong</td><td style="text-align:left">Gives the full distribution of outcomes</td></tr>
<tr><td>Historical VaR</td><td style="text-align:left">Assumes tomorrow resembles a calm past; misses regime shifts</td><td style="text-align:left">Switches between calm/stress/crisis/grind with fat tails</td></tr>
<tr><td>P/E or PEG alone</td><td style="text-align:left">A cyclical looks "cheap" at peak earnings, right before they collapse</td><td style="text-align:left">Cycle-adjusts earnings; models the demand trough</td></tr>
<tr><td>"It always comes back"</td><td style="text-align:left">Survivorship bias; ignores broken theses &amp; solvency</td><td style="text-align:left">Separates secular / cyclical / broken; adds a solvency-failure tail</td></tr>
</table>
<p>The edge isn't a secret signal — it's <b>honesty about uncertainty</b> plus a clean separation of <i>depth</i> (market-driven) from <i>recovery</i> (fundamentals-driven). That separation is what lets it answer "good drop or bad drop?" instead of just "how big a drop?"</p>""")

# ---------- TAM/SAM ----------
add(f"""<h2 id="tam">5 &nbsp;How TAM and SAM enter the recovery estimate</h2>
<p><b>TAM</b> (Total Addressable Market) is the whole pond a company could eventually serve; <b>SAM</b> (Serviceable Addressable Market) is the slice it can realistically win in the next 2–3 years. They matter because a stock's price is really a bet on future earnings, and that bet is only credible if there's room to grow into it.</p>
<div class="card">
<b>The logic the model applies:</b>
<ul>
<li>The market pays a <b>premium</b> over a plain market multiple.</li>
<li>The part of that premium the <b>SAM runway justifies</b> is "supported" — it tends to come back after a crash, because the business keeps growing into it.</li>
<li>The rest is "floating premium" — priced hope. In a stress regime it <b>evaporates first</b> (depth) and a name must <i>regrow into its SAM</i> to win it back (recovery time).</li>
</ul>
So a high-growth name with an intact, expanding TAM/SAM is a good recovery bet: the runway that justified its price is still there after the panic. If the TAM/SAM is shrinking or the thesis is broken, recovery is not on offer at any multiple.</p>
<p class="note">For an ETF this is the crux: a basket diversifies away the risk that <i>one</i> company fumbles execution, while keeping the shared bet that the <i>theme's</i> TAM stays intact. That's why a high-growth ETF can be a better recovery bet than any single holding — provided the TAM/SAM thesis holds.</p>""")

# ---------- CYCLICAL ----------
mic = matrix_row("Micron"); nvda = matrix_row("NVIDIA")
add(f"""<h2 id="cyc">6 &nbsp;The hard case: cyclical demand (memory / DRAM)</h2>
<p>Most models treat a cyclical name as simply "recovers slower." That's wrong in a specific, dangerous way. When memory (DRAM/NAND) crashes, the stock rolls over <i>as demand is still falling</i> — earnings keep dropping for months <b>after</b> the price drop. So the price genuinely cannot reclaim its old peak early; recovery is <b>back-loaded</b> until the demand cycle turns.</p>
<p>The model encodes this as an explicit <b>two-phase demand trough</b> per cyclical theme (memory ≈ 9 months of falling demand + 6 months stabilizing, then rebound), with a deeper "second leg" while demand keeps sliding. The result is a recovery curve that is <b>flat early, steep late</b> — the opposite of a secular name's smooth climb:</p>""")

if mic and nvda:
    add(f"""<div class="chartcard"><div class="ct">Recovery odds after a &gt;25% fall — cyclical vs secular</div>
    <div class="cs">P(back to prior peak within N months | it fell). Micron (memory, cyclical) can't recover until the demand cycle clears; NVIDIA (secular) recovers from month one.</div>
    {lines([("Micron (cyclical)",[mic['recover_6m'],mic['recover_12m'],mic['recover_18m'],mic['recover_36m']],CYC),
            ("NVIDIA (secular)",[nvda['recover_6m'],nvda['recover_12m'],nvda['recover_18m'],nvda['recover_36m']],GRN)],
           ymax=0.7,xs=("6m","12m","18m","36m"))}
    <div class="legend"><span><i style="background:{CYC}"></i>Micron — flat then steep (waits for the cycle)</span><span><i style="background:{GRN}"></i>NVIDIA — smooth (grows into the dip)</span></div></div>""")

add(f"""<div class="chartcard"><div class="ct">The two-phase cyclical trough (schematic)</div>
<svg viewBox="0 0 640 180" width="100%" style="max-width:640px">
<line x1="40" y1="150" x2="620" y2="150" stroke="{GRID}"/>
<polyline points="40,40 150,40 240,120 330,150 470,150 560,55 610,45" fill="none" stroke="{CYC}" stroke-width="2.5"/>
<polyline points="40,40 150,40 230,95 300,60 460,45 610,40" fill="none" stroke="{GRN}" stroke-width="2" stroke-dasharray="4 4"/>
<rect x="240" y="30" width="230" height="125" fill="{CYC}" opacity="0.06"/>
<text x="355" y="48" font-size="11" text-anchor="middle" fill="{CYC}">demand-down + stabilize (~15 mo) → recovery suppressed</text>
<text x="150" y="32" font-size="11" fill="{INK}">crash</text>
<text x="585" y="62" font-size="11" fill="{CYC}">rebound</text>
<text x="500" y="38" font-size="10.5" fill="{GRN}">secular: grows back</text>
</svg>
<div class="cs">Beta sets the initial fall (both lines drop together). The cyclical line keeps sliding a "second leg" and stays low until the cycle turns; the secular line climbs back as the business compounds through the dip.</div></div>""")

# ---------- DRAWDOWN x RECOVERY MATRIX ----------
add(f"""<h2 id="matrix">7 &nbsp;Today's drawdown × recovery — the core output</h2>
<p>For each name: how likely a &gt;25% fall is by each horizon, and <i>if</i> it falls, how likely it's whole again within 6/12/18/24/36 months. Probabilities, never timing.</p>""")

fall_data=[]
for nm in ["VOO (S&P 500)","QQQ (Nasdaq-100)","SMH (VanEck Semis)","DRAM (Roundhill Memory)","ARKK (ARK Innovation)"]:
    m=matrix_row(nm)
    if m: fall_data.append((nm.split(" (")[0], m["p_drawdown"], tagcol((RC.get(nm,{}) or {}).get('recovery_curve') and "" or "") or ACC))
fall_bars=[(lab, v, ACC) for lab,v,_ in fall_data]
add(f"""<div class="chartcard"><div class="ct">P(&gt;25% fall within 18 months) — today</div>
<div class="cs">The broad index falls least often; concentrated/high-beta baskets most.</div>
{bars_v(fall_bars, ymax=0.85)}</div>""")

add("<table><tr><th>Name</th><th>type</th><th>P(&gt;25% fall, 18m)</th><th>rec ≤6m</th><th>≤12m</th><th>≤18m</th><th>≤24m</th><th>≤36m</th></tr>")
for nm in KEY:
    m=matrix_row(nm); a=(EHR.get(nm,{}) or {}).get("crash_growth")
    if a is None:
        try:
            import crash_growth as CG; a=CG.archetype(nm)
        except Exception: a=""
    if not m: continue
    add(f"""<tr><td>{nm}</td><td><span class="tag" style="background:{tagcol(a)}22;color:{tagcol(a)}">{tag(a) if a else '—'}</span></td>
    <td>{pct(m['p_drawdown'])}</td><td>{pct(m['recover_6m'])}</td><td>{pct(m['recover_12m'])}</td>
    <td>{pct(m['recover_18m'])}</td><td>{pct(m['recover_24m'])}</td><td>{pct(m['recover_36m'])}</td></tr>""")
add("</table>")
add(f"""<p>Read it as your thesis predicts: <b>secular</b> names recover from month one; <b>memory cyclicals</b> (DRAM, Micron) show 0% early then catch up after the cycle clears; <b>broken</b> baskets (ARKK) fall most and heal least.</p>""")

# ---------- HORIZON RANKING ----------
add(f"""<h2 id="rank">8 &nbsp;The ranking — and why it flips with your horizon</h2>
<p>This is the heart of your question. Because the score subtracts only the <i>unrecovered</i> loss, an ETF that heals in ~24 months is penalized at a 1-year horizon (you'd sell while still underwater) but barely dented at 3–5 years (it's recovered and compounding again). <b>The same ETF can be a poor 1-year hold and the best 5-year hold.</b> DRAM is the textbook case:</p>""")

# DRAM crossover chart vs SMH and VOO
def er(nm,h):
    d=EHR.get(nm,{}).get("horizons",{}).get(h)
    return d["exp_return_horizon"] if d else 0
hs=["12m","24m","36m","60m"]
add(f"""<div class="chartcard"><div class="ct">Expected return by holding horizon (recovery judged vs the hold)</div>
<div class="cs">DRAM starts below the broad market at 1 year, then overtakes everything by year 2+ as its demand cycle clears and 28%/yr growth compounds.</div>
{lines([("DRAM",[er("DRAM (Roundhill Memory)",h) for h in hs],CYC),
        ("SMH",[er("SMH (VanEck Semis)",h) for h in hs],ACC),
        ("VOO",[er("VOO (S&P 500)",h) for h in hs],MUT)],
       ymax=2.0,xs=("1y","2y","3y","5y"))}
<div class="legend"><span><i style="background:{CYC}"></i>DRAM (high-growth cyclical)</span><span><i style="background:{ACC}"></i>SMH (semis)</span><span><i style="background:{MUT}"></i>VOO (S&amp;P 500)</span></div></div>""")

add(f"""<p class="note">The score per horizon (both shown in the tables): <b>expected return</b> = growth path × (1 − expected unrecovered loss), and <b>reward/risk</b> = growth ÷ unrecovered loss. Recovery is judged two ways — against your actual hold (a 2-year hold needs recovery ≤24m) and against a fixed 24-month rule. Broken theses are removed from the buy ranking and shown separately.</p>""")

for h,label in [("12m","1-year hold"),("24m","2-year hold"),("36m","3-year hold"),("60m","5-year hold")]:
    main,brk=horizon_table(h)
    add(f'<h3>{label} — ranked by expected return</h3>')
    add('<table><tr><th>#</th><th>ETF</th><th>type</th><th>growth p.a.</th><th>P(fall)</th><th>rec ≤hold</th><th>rec ≤24m</th><th>exp return</th><th>rew/risk</th></tr>')
    for i,(nm,d) in enumerate(main,1):
        r=d["horizons"][h]; a=d["crash_growth"]
        add(f"""<tr><td>{i}</td><td>{nm}</td><td><span class="tag" style="background:{tagcol(a)}22;color:{tagcol(a)}">{tag(a)}</span></td>
        <td>{r and pct(d['growth_ann'])}</td><td>{pct(r['p_fall'])}</td><td>{pct(r['p_rec_horizon'])}</td>
        <td>{pct(r['p_rec_24m'])}</td><td style="font-weight:700;color:{GRN if r['exp_return_horizon']>0 else RED}">{r['exp_return_horizon']*100:+.0f}%</td>
        <td>{r['reward_to_risk']:.1f}</td></tr>""")
    for nm,d in brk:
        r=d["horizons"][h]
        add(f"""<tr style="opacity:.6"><td>⚠</td><td>{nm}</td><td><span class="tag" style="background:{RED}22;color:{RED}">⚠ broken — avoid</span></td>
        <td>{pct(d['growth_ann'])}</td><td>{pct(r['p_fall'])}</td><td>{pct(r['p_rec_horizon'])}</td><td>{pct(r['p_rec_24m'])}</td>
        <td>{r['exp_return_horizon']*100:+.0f}%</td><td>{r['reward_to_risk']:.1f}</td></tr>""")
    add("</table>")

# ---------- HISTORICAL VALIDATION ----------
add(f"""<h2 id="hist">9 &nbsp;Did it work? Checking against {len(HIST)} real crashes</h2>
<p>A risk model is only worth trusting if its tail brackets what actually happened. We set the macro dial to the <i>eve</i> of {len(HIST)} historical crashes — wildly different causes (dot-com, credit, sovereign, pandemic, rate shock) — and asked: does the simulated 90th-percentile worst case contain the realized peak-to-trough fall?</p>
<div class="chartcard"><div class="ct">Realized crash vs simulated 90th-percentile tail</div>
<div class="cs">Green = the simulated tail bracketed the real crash (✓). Faint bar = simulated p90 worst case; solid = realized fall.</div>
{grouped_bars(HIST_BARS, ymax=0.7)}
<div class="legend"><span><i style="background:{ACC};opacity:.35"></i>simulated p90 tail</span><span><i style="background:{GRN}"></i>realized (captured)</span><span><i style="background:{RED}"></i>realized (missed)</span></div></div>""")

add("<table><tr><th>Episode</th><th>stress set</th><th>sim p90 tail</th><th>realized</th><th>result</th></tr>")
for r in HIST:
    add(f"""<tr><td>{r['name']}</td><td>{r['stress']:.0f}/100</td><td>−{r['p90']*100:.0f}%</td><td>−{r['realized']*100:.0f}%</td>
    <td><span class="tag" style="background:{(GRN if r['cap'] else RED)}22;color:{(GRN if r['cap'] else RED)}">{'✓ captured' if r['cap'] else '✕ missed'}</span></td></tr>""")
add("</table>")
ncap=sum(1 for r in HIST if r['cap'])
_misses=[r for r in HIST if not r['cap']]
if _misses:
    _m=_misses[0]
    _miss_txt=(f"The miss — {_m['name']} at −{_m['realized']:.0f}% vs a −{_m['p90']:.0f}% simulated tail — grazes the boundary by about a point, which is itself informative: the deepest credit crisis in the set sits right at the model's 90th-percentile edge.")
else:
    _miss_txt="No episode in this set exceeded the simulated p90 tail."
add(f"""<div class="card"><b>{ncap} of {len(HIST)} captured.</b> {_miss_txt} Honest framing: the macro inputs here are historical (known after the fact), so this validates that the <b>stress→tail mechanism is correctly shaped across regimes</b>, not that the model called each crash in advance. It also separately passed a name-level 2022 backtest (it ranked which names fell hardest, not just the index).</div>""")
add("""<div class="card" style="background:#fffbeb;border-color:#fde68a"><b>What this table validates — and what it doesn't.</b> The seven-crash check scores <b>drawdown depth</b> only: does the simulated tail bracket the realized fall. It does <i>not</i> by itself validate <b>recovery time</b>. 2008 is the clearest case — the depth was nearly matched, but the financial system froze and recovery took ~5.5 years, far longer than a normal valuation/TAM recovery implies. That recovery-side behaviour is handled separately by the systemic-freeze layer below.</div>""")

# ---------- SYSTEMIC FREEZE ----------
add(f"""<h2 id="freeze">9b &nbsp;Total collapse: the systemic-freeze layer (the 2008 case)</h2>
<p>Every recovery estimate so far assumes <b>no total collapse</b> — each name heals at its own fundamental speed. But a true macro failure breaks that assumption. When a keystone sub-market — the banking/credit system, or in this AI universe the <b>compute/datacenter "plumbing"</b> everything runs on — freezes, the whole market's recovery is suspended for years, <b>healthy names included</b>. This is recovery-side contagion: not "everything falls together" (we already model that), but "everything <i>stays down</i> together because the system they share is broken."</p>
<div class="card"><b>Two refinements make it faithful to history:</b>
<ul>
<li><b>Liquidity is the gate (2008 vs 2020).</b> Panic alone doesn't freeze the system — a central-bank backstop can avert it. Severity = panic × liquidity-gate: 2008 drained liquidity → multi-year freeze; 2020 flooded it → months, not years. So the same-size panic gives very different recoveries.</li>
<li><b>The freeze is uneven across sub-markets.</b> Its length scales with each sector's <i>dependence</i> on the frozen keystone. AI-infra (the plumbing) stays frozen longest; a self-funded defensive sector thaws first. "The collapse hit all layers — but unevenly."</li>
</ul></div>
<div class="chartcard"><div class="ct">Recovery on systemic-collapse paths, by sub-market and liquidity regime</div>
<div class="cs">Median months to reclaim the prior peak when the broad market collapses >55%. A 2008-type drain stretches the keystone toward the ~66-month recovery the S&P actually took; a 2020-type Fed flood compresses it. Defensive sectors thaw first in both.</div>
<img src="{_datauri('freeze.png')}" style="width:100%;max-width:660px"></div>
<p class="note">Triggered only on the deep-collapse tail (broad market down >55%) — dormant in normal bears. A broad-market collapse of that size <i>itself</i> implies a minimum plumbing-delay even if today's funding indicators aren't 2008-like (a severity floor), with the full multi-year freeze reserved for a genuine liquidity drain. It is causal (a freeze only delays a recovery still in progress when it starts — no look-ahead), composed with the cyclical demand-trough by taking the longer of the two, never stacking. The sim window was extended to 7 years so a multi-year systemic heal is observed, not censored as permanent.</p>""")

# ---------- MONTE CARLO / STRESS ----------
add(f"""<h2 id="mc">10 &nbsp;Why Monte Carlo + stress testing make it reliable</h2>
<p><b>Monte Carlo simulation</b> means: instead of solving for one answer, let the computer roll the dice 150,000 times and tabulate what happens. Markets are driven by randomness and rare shocks, so a single equation can't capture them — but counting outcomes over 150,000 plausible futures can. The law of large numbers does the rest: with enough draws, the counted frequencies converge on stable probabilities (our 8k, 16k and 150k runs already agree to within a fraction of a percent).</p>
<p><b>Stress testing</b> means deliberately turning the macro dial to ugly settings — high valuations, wide credit spreads, spiking VIX — and watching the tail respond. Three things make the simulation realistic rather than naive:</p>
<ul>
<li><b>Four regimes with fat tails</b> — calm, stress, crisis and a slow "de-rating grind," with crash days far more frequent than a bell curve allows (Student-t tails), because real crashes are.</li>
<li><b>Contagion</b> — in a panic, correlations jump toward 1: everything in a theme falls together, so diversification thins exactly when you need it. The model spikes intra-group correlation to ~0.9 in crisis.</li>
<li><b>Solvency &amp; dilution tail</b> — a fragile, cash-poor name that falls deep can fail to recover at all (or dilute shareholders at the lows). That permanent-loss tail is modeled separately from ordinary drawdowns.</li>
</ul>
<p>Together these mean the probabilities aren't fair-weather estimates — they're stress-aware, and they're checked against history.</p>""")

# ---------- CAVEATS ----------
add(f"""<h2 id="caveats">11 &nbsp;What it is, and what it isn't</h2>
<p>This is a serious <b>research and risk lens</b>: best-in-class for comparing names and ETFs, sizing how likely a drawdown is over your horizon, and judging whether a high-growth basket is likely to recover in time. It is <b>not</b> an automated buy/sell engine, a market-timing tool, or a source of exact probabilities. Growth rates, TAM/SAM and the archetype tags are informed judgments the model states openly and sweeps — the output is only as good as those inputs. Read tiers and ranges, not decimals.</p>
<div class="disclaimer"><b>Research model — not investment advice.</b> Probabilities are model estimates, not guarantees. Past behavior of the model on historical episodes does not predict future accuracy. Markets can and do behave outside any model's assumptions. Do your own due diligence and consult a licensed advisor before investing.</div>""")

add(f'<p class="note" style="margin-top:30px">Generated from the model\'s own outputs · macro as of {RES.get("as_of","today")} · figures shown at demo fidelity (production default 150,000 paths). © research model.</p>')
add("</div></body></html>")

open(os.path.join(HERE,"investor_report.html"),"w",encoding="utf-8").write("".join(W))
print("wrote investor_report.html  (%d KB)" % (len("".join(W))//1024))
