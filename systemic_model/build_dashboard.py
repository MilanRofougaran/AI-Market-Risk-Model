"""
============================================================================
 BUILD_DASHBOARD  --  systemic_model
============================================================================
 Regenerates a self-contained HTML dashboard from the LATEST run, every time
 it is called. Two views in one page:

   1. The growth-tiered ranking (ETFs as subgroups + top stock per theme),
      each name showing expected 18m growth, permanent-loss risk, AND change
      arrows: how the risk moved since yesterday and over the last 30 days.
   2. A "what changed" panel: cumulative 30-day drift, slow-creep items, and
      anything that crossed or is approaching a danger line.

 Inputs : results.json (current model output) + drift_history.json (the ledger
          maintained by track_changes.py).
 Output : tier_dashboard.html  (open it in a browser; it has no dependencies).

 Drop this into the daily run after track_changes --record and the page is
 always current, with the movement baked in. RESEARCH MODEL, NOT ADVICE.
============================================================================
"""
import datetime as dt
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

import tiering as T

RESULTS = os.path.join(HERE, "results.json")
HISTORY = os.path.join(HERE, "drift_history.json")
OUT = os.path.join(HERE, "tier_dashboard.html")


def _load(p, default=None):
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return default


def _deltas(history):
    """For each name: (delta_1d, delta_30d) in permanent-loss prob, using the
    ledger. Positive = riskier."""
    h = (history or {}).get("history", [])
    if len(h) < 2:
        return {}, None, None
    latest = h[-1]
    prev = h[-2]
    # earliest within 30 days of latest
    ld = dt.date.fromisoformat(latest["date"])
    cutoff = ld - dt.timedelta(days=30)
    win = [e for e in h if dt.date.fromisoformat(e["date"]) >= cutoff]
    d30base = win[0] if win else h[0]
    out = {}
    for nm, c in latest["companies"].items():
        now = c.get("p_deep_permanent")
        p = prev["companies"].get(nm, {}).get("p_deep_permanent")
        b = d30base["companies"].get(nm, {}).get("p_deep_permanent")
        out[nm] = (
            (now - p) if (now is not None and p is not None) else None,
            (now - b) if (now is not None and b is not None) else None,
        )
    return out, d30base["date"], latest["date"]


def _arrow(d):
    if d is None:
        return '<span class="flat">—</span>'
    pp = round(d * 100)
    if pp >= 1:
        return f'<span class="up">▲ +{pp}pp</span>'
    if pp <= -1:
        return f'<span class="down">▼ {pp}pp</span>'
    return '<span class="flat">●</span>'


def _curve(res, name, months):
    c = res["companies"]["recovery_cond"].get(name, {})
    for pt in c.get("recovery_curve", []) or []:
        if pt["months"] == months:
            return pt["p_recovered"]
    return 0.0


def _buckets(res, name):
    """Unconditional recovery outcome split (sums to 1, comparable across names):
       no_fall, ≤1y, 1-2y, 2-3y, >3y(long/uncertain). The >3y slice is the tail
       risk — chance a >25% fall takes many years to heal."""
    c = res["companies"]["recovery_cond"].get(name, {})
    pdd = c.get("p_dd25") or 0.0
    p12, p24, p36 = _curve(res, name, 12), _curve(res, name, 24), _curve(res, name, 36)
    return dict(no_fall=max(0.0, 1 - pdd),
                le1=pdd * p12, y12=pdd * max(0, p24 - p12),
                y23=pdd * max(0, p36 - p24), gt3=pdd * max(0, 1 - p36))


def _tail_class(r):
    if r is None:
        return "rk-na"
    if r <= 0.22:
        return "rk-lo"
    if r <= 0.26:
        return "rk-mid"
    return "rk-hi"


def build(kind=None, cap=None, out_path=None, csv_path=None, title_suffix=""):
    res = _load(RESULTS)
    if not res:
        print("No results.json — run the model first.")
        return None
    out_path = out_path or OUT
    csv_path = csv_path or os.path.join(HERE, "tier_table.csv")
    hist = _load(HISTORY, {"history": []})
    deltas, d30_date, today = _deltas(hist)
    rows = T.build_rows(res)
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    tiers = T.tier_rows(rows)
    if cap:
        tiers = [(lbl, mem[:cap]) for lbl, mem in tiers]
    as_of = res.get("as_of", "?")
    gen = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        import macro_stress as _MS
        _st = _MS.compute(res.get("macro", {})) if res.get("macro") else None
        stress_banner = ("" if not _st else
            f'<div style="background:#f1efe8;border-radius:10px;padding:8px 13px;margin-bottom:14px;font-size:12px;color:#5f5e5a">'
            f'<b>Macro-stress index {round(_st["score"]*100)}/100</b> ({_MS.stress_label(_st["score"])}) '
            f'— structural fragility {round(_st["structural"]*100)}, acute trigger {round(_st["acute"]*100)} '
            f'· scales every name\'s drawdown odds by x{_MS.crisis_mult(_st["score"]):.2f} vs a neutral backdrop.</div>')
    except Exception:
        stress_banner = ""

    # concentration / correlation banner (from correlation_report.json if present)
    conc_banner = ""
    try:
        cr = _load(os.path.join(HERE, "correlation_report.json"))
        if cr and cr.get("baskets"):
            uni = next((b for b in cr["baskets"] if "universe" in b["label"].lower()), cr["baskets"][0])
            conc_banner = (
                f'<div style="background:#fceBEB;border-radius:10px;padding:8px 13px;margin-bottom:14px;font-size:12px;color:#a32d2d">'
                f'<b>Concentration warning</b> — these names are mostly ONE bet (the AI-capex cycle): '
                f'~{uni["neff_with"]:.0f} effective independent bets across {uni["n"]} names '
                f'(avg correlation {uni["rho_with"]:.2f}). A specialized ETF ≈ 0.95 correlated with its lead '
                f'holding, so it barely diversifies. P(equal-weight basket falls &gt;25% in 18m) ≈ '
                f'{uni["port_dd25_with"]*100:.0f}%. Size to the bet, not the name count.</div>')
    except Exception:
        conc_banner = ""

    # cumulative drift summary (reuse track_changes if 2+ snapshots)
    changes = []
    try:
        import io
        import contextlib
        import track_changes as TC
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            TC.cumulative(days=30)
        for line in buf.getvalue().splitlines():
            s = line.strip()
            if s.startswith("- ") or s.startswith("** "):
                changes.append(s)
    except Exception:
        pass

    def tier_html(label, members):
        cards = []
        for r in members:
            g = r["growth"]
            b = _buckets(res, r["name"])
            tail = b["gt3"]
            d1, d30 = deltas.get(r["name"], (None, None))
            gw = round(min(g / 0.80, 1.0) * 100)
            def w(x):
                return round(x * 100, 1)
            cards.append(f"""
            <div class="row">
              <div class="nm">{html.escape(r['name'])}
                <span class="badge {'etf' if r['kind']=='ETF' else 'stk'}">{r['kind']}</span></div>
              <div class="th">{html.escape(r['theme'])}</div>
              <div class="gw"><div class="bar"><i style="width:{gw}%"></i></div><b>{round(g*100)}%</b></div>
              <div class="rec" title="if it falls >25%: recovers ≤1y / 1-2y / 2-3y / takes >3y">
                <span class="seg nofall" style="width:{w(b['no_fall'])}%"></span><span class="seg s1" style="width:{w(b['le1'])}%"></span><span class="seg s2" style="width:{w(b['y12'])}%"></span><span class="seg s3" style="width:{w(b['y23'])}%"></span><span class="seg s4" style="width:{w(b['gt3'])}%"></span>
              </div>
              <div class="tail {_tail_class(tail)}">{round(tail*100)}%</div>
              <div class="chg">{_arrow(d30)}</div>
            </div>""")
        return f'<h3>{html.escape(label)}</h3><div class="tier">{"".join(cards)}</div>'

    tiers_html = "".join(tier_html(lbl, mem) for lbl, mem in tiers if mem)

    # ---- exact-numbers table + CSV export ----
    import csv as _csv
    def _tier_name(g):
        return "High" if g > 0.40 else ("Moderate" if g >= 0.15 else "Safe")
    tbl = []
    shown = [(r["name"], r["kind"], r["growth"],
              "Trading" if lbl.startswith("Trading") else None)
             for lbl, mem in tiers for r in mem]
    for name, knd, g, forced_tier in shown:
        c = res["companies"]["recovery_cond"].get(name)
        if not c:
            continue
        pdd = c.get("p_dd25") or 0.0
        p12, p24, p36 = _curve(res, name, 12), _curve(res, name, 24), _curve(res, name, 36)
        tail = pdd * max(0.0, 1 - p36)
        d30 = deltas.get(name, (None, None))[1]
        tbl.append((name, knd, forced_tier or _tier_name(g), g, pdd, p12, p24, p36, tail, d30))
    # S&P (VOO) true-permanent loss = the benchmark the multiples are measured against
    # benchmarks: raw >3y tail (still-underwater-at-3.5y). reward = (g/bench_g)x(bench_tail/tail)
    sp_tail = _buckets(res, "VOO (S&P 500)")["gt3"] or 0.21
    sp_growth = T.UNIVERSE.get("VOO (S&P 500)", (None, None, 0.09))[2]
    sc_tail = _buckets(res, "SCHD (Dividend)")["gt3"] or 0.19
    sc_growth = T.UNIVERSE.get("SCHD (Dividend)", (None, None, 0.06))[2]
    def _xsp(nm, tail):
        return (tail / sp_tail) if sp_tail > 1e-6 else None
    def _vssp(nm, g, tail):
        return ((g / sp_growth) * (sp_tail / tail)) if (tail > 1e-6 and sp_growth > 1e-6) else None
    def _vssc(nm, g, tail):
        return ((g / sc_growth) * (sc_tail / tail)) if (tail > 1e-6 and sc_growth > 1e-6) else None
    # crash-growth archetype disambiguates the growth TIER from how a name RECOVERS:
    # a "High"-growth tier name can be secular (holds/accelerates), cyclical (DRAM:
    # dips-then-rebounds), or broken (ARKK: thesis impaired). GPT review: do not let
    # all three collapse to a bare "High".
    try:
        import crash_growth as _CG
        def _arch(nm): return _CG.archetype(nm)
    except Exception:
        def _arch(nm): return ""
    # recovery_rank: the crash-growth-aware verdict (secular high-growth / cyclical
    # rebound-dependent / PEG-fast MC-uncertain / broken avoid / diversified-safe) so the
    # master CSV never shows a bare "High" for a broken or cyclical name. Read from the
    # fresh growth_recovery.json (written just before build_dashboard in run_all). (GPT review.)
    _rank_map = {}
    try:
        _gr = json.load(open(os.path.join(HERE, "growth_recovery.json")))
        _rank_map = _gr.get("recovery_rank", {}) or {}
    except Exception:
        _rank_map = {}
    def _rrank(nm):
        if nm in _rank_map:
            return _rank_map[nm]
        a = _arch(nm)
        return ("broken thesis — avoid unless evidence changes" if a == "broken"
                else "cyclical high-growth / rebound-dependent" if a == "cyclical" else "")
    with open(csv_path, "w", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["name", "type", "growth_tier", "crash_growth", "recovery_rank",
                    "exp_growth_18m", "P(>25% fall)",
                    # conditional recovery on the user's 6/12/18m grid (P recovered within X
                    # months | a >25% fall happened within the 18m horizon). The "_by18m"
                    # suffix is explicit that this is the 18m-drawdown cohort -- the full
                    # drawdown-horizon x recovery-horizon matrix is in results.json/report.
                    "recover_6m_if_falls_by18m", "recover_12m_if_falls_by18m", "recover_18m_if_falls_by18m",
                    "recover_by_1y_if_falls", "recover_by_2y_if_falls",
                    "recover_by_3y_if_falls", "gt3y_tail_unconditional",
                    "permanence_factor", "true_permanent_loss",
                    "perm_vs_SP_multiple", "reward_vs_SP", "reward_vs_SCHD",
                    "growth_per_fall", "delta_tail_30d"])
        for (nm, kd, tr, g, pdd, p12, p24, p36, tail, d30) in tbl:
            perm = T.PERMANENCE.get(nm, T.DEFAULT_PERMANENCE)
            tp = tail * perm
            xsp = _xsp(nm, tail)
            vssp = _vssp(nm, g, tail)
            vssc = _vssc(nm, g, tail)
            gpf = round(g / pdd, 2) if pdd > 1e-6 else ""
            r6, r12, r18 = _curve(res, nm, 6), _curve(res, nm, 12), _curve(res, nm, 18)
            w.writerow([nm, kd, tr, _arch(nm), _rrank(nm), round(g, 3), round(pdd, 3),
                        round(r6, 3), round(r12, 3), round(r18, 3),
                        round(p12, 3), round(p24, 3), round(p36, 3), round(tail, 3),
                        perm, round(tp, 3), (round(xsp, 1) if xsp else ""),
                        (round(vssp, 2) if vssp else ""), (round(vssc, 2) if vssc else ""),
                        gpf, (round(d30, 3) if d30 is not None else "")])

    def _tcell(tail):
        cls = "t-lo" if tail <= 0.22 else ("t-mid" if tail <= 0.26 else "t-hi")
        return f'<td class="{cls}">{round(tail*100)}%</td>'
    def _dcell(d):
        if d is None:
            return '<td style="color:var(--mut)">new</td>'
        pp = round(d * 100)
        if pp >= 1:
            return f'<td class="up">+{pp}</td>'
        if pp <= -1:
            return f'<td class="down">{pp}</td>'
        return '<td style="color:var(--mut)">0</td>'
    def _vscell(v):
        if v is None:
            return '<td>—</td>'
        v = round(v, 2)
        c = "t-lo" if v >= 1.0 else ("t-mid" if v >= 0.7 else "t-hi")
        return f'<td class="{c}"><b>{v}</b></td>'
    trs = "".join(
        f'<tr><td class="l">{html.escape(nm)}</td><td class="l">{kd}</td>'
        f'<td class="l">{tr}</td><td>{round(g*100)}%</td><td>{round(pdd*100)}%</td>'
        f'<td>{round(p24*100)}%</td>'
        f'{_tcell(tail)}'
        f'<td>{round(_xsp(nm,tail),2) if _xsp(nm,tail) else "—"}×</td>'
        f'{_vscell(_vssp(nm,g,tail))}{_vscell(_vssc(nm,g,tail))}'
        f'{_dcell(d30)}</tr>'
        for (nm, kd, tr, g, pdd, p12, p24, p36, tail, d30) in tbl)
    table_html = f"""
    <div class="panel"><h3>All numbers <span class="sub">(full set, incl. recovery-by-1/2/3y, exported to tier_table.csv)</span></h3>
      <table class="dt"><thead><tr>
        <th class="l">Name</th><th class="l">Type</th><th class="l">Tier</th>
        <th>Growth</th><th>P(&gt;25% fall)</th><th>↻2y</th><th>&gt;3y tail</th>
        <th>×S&amp;P</th><th>vs&nbsp;S&amp;P</th><th>vs&nbsp;SCHD</th><th>Δ30d</th>
      </tr></thead><tbody>{trs}</tbody></table>
      <p class="sub" style="margin-top:8px">↻2y = chance of recovering within 2y if it falls &gt;25%. <b>&gt;3y tail</b> = still-underwater-at-~3.5y probability. <b>×S&amp;P</b> = &gt;3y tail ÷ the S&amp;P's &gt;3y tail (risk relative to the index). <b>vs S&amp;P / vs SCHD</b> = (growth ÷ benchmark growth) × (benchmark tail ÷ name tail) — reward-to-risk normalized so benchmark = <b>1.00</b>. Above 1 = more growth per unit of long-drawdown risk than the benchmark; below 1 = less. (e.g. DRAM = (45÷9)×(21÷24) ≈ 4.4.)</p>
    </div>"""

    changes_html = ""
    if changes:
        items = "".join(f"<li>{html.escape(c[2:] if c.startswith('- ') else c)}</li>"
                        for c in changes)
        span = f"{d30_date} → {today}" if d30_date else "building…"
        changes_html = f"""
        <div class="panel">
          <h3>What changed · last 30 days <span class="sub">({html.escape(str(span))})</span></h3>
          <ul class="chglist">{items}</ul>
        </div>"""
    else:
        changes_html = """<div class="panel"><h3>What changed · last 30 days</h3>
          <p class="sub">Ledger is still building — cumulative drift appears once there are 2+ daily snapshots.</p></div>"""

    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Systemic + TAM — live dashboard</title>
<style>
:root{{--bg:#faf9f5;--card:#fff;--ink:#1c1c1a;--mut:#6b6a64;--line:#e7e5dd;
--lo-b:#e1f5ee;--lo-t:#0f6e56;--mid-b:#faeeda;--mid-t:#854f0b;--hi-b:#fceBEB;--hi-t:#a32d2d;
--up:#a32d2d;--down:#0f6e56;--info-b:#e6f1fb;--info-t:#185fa5;}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
background:var(--bg);color:var(--ink);margin:0;padding:24px;line-height:1.5}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:22px;font-weight:600;margin:0 0 2px}}
.meta{{color:var(--mut);font-size:13px;margin-bottom:18px}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--mut);margin-bottom:14px}}
.legend i{{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:middle;margin-right:4px}}
.explain{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px}}
.explain .b{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 14px}}
.explain .b h4{{margin:0 0 3px;font-size:13px;font-weight:600}}
.explain .b p{{margin:0;font-size:12px;color:var(--mut);line-height:1.5}}
@media(max-width:640px){{.explain{{grid-template-columns:1fr}}}}
h3{{font-size:15px;font-weight:600;margin:22px 0 8px}}
.sub{{color:var(--mut);font-weight:400;font-size:12px}}
.tier{{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--card)}}
.row{{display:grid;grid-template-columns:138px 104px 88px 1fr 46px 56px;align-items:center;
gap:9px;padding:7px 14px;border-bottom:1px solid var(--line);font-size:13px}}
.row:last-child{{border-bottom:none}}
.nm{{font-weight:600}}
.badge{{font-size:9px;padding:1px 4px;border-radius:4px;margin-left:4px;font-weight:500}}
.badge.etf{{background:#f1efe8;color:#5f5e5a}} .badge.stk{{background:var(--info-b);color:var(--info-t)}}
.th{{color:var(--mut);font-size:12px}}
.gw{{display:flex;align-items:center;gap:7px}}
.bar{{flex:1;height:7px;background:#efeee8;border-radius:4px;overflow:hidden}}
.bar i{{display:block;height:100%;background:var(--info-t);border-radius:4px}}
.gw b{{font-weight:600;min-width:30px}}
.rec{{display:flex;height:11px;border-radius:3px;overflow:hidden;background:#efeee8}}
.seg{{height:100%}} .seg.nofall{{background:#efeee8}}
.seg.s1{{background:#1d9e75}} .seg.s2{{background:#9fe1cb}} .seg.s3{{background:#ef9f27}} .seg.s4{{background:#e24b4a}}
.tail{{text-align:center;font-weight:600;padding:2px 0;border-radius:6px;font-size:12px}}
.rk-lo{{background:var(--lo-b);color:var(--lo-t)}} .rk-mid{{background:var(--mid-b);color:var(--mid-t)}}
.rk-hi{{background:var(--hi-b);color:var(--hi-t)}} .rk-na{{color:var(--mut)}}
.chg{{font-size:11px;text-align:right;white-space:nowrap}}
.up{{color:var(--up);font-weight:600}} .down{{color:var(--down);font-weight:600}} .flat{{color:var(--mut)}}
.panel{{margin-top:24px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px}}
.chglist{{margin:6px 0 0;padding-left:18px}} .chglist li{{margin:3px 0;font-size:13px}}
.foot{{color:var(--mut);font-size:11px;margin-top:22px}}
table.dt{{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}}
table.dt th,table.dt td{{padding:5px 7px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
table.dt th{{color:var(--mut);font-weight:500;font-size:11px;border-bottom:1px solid var(--mut)}}
table.dt td.l,table.dt th.l{{text-align:left}}
table.dt tr:hover{{background:var(--bg)}}
td.t-lo{{color:var(--lo-t);font-weight:600}} td.t-mid{{color:var(--mid-t);font-weight:600}} td.t-hi{{color:var(--hi-t);font-weight:600}}
.up{{color:var(--up)}} .down{{color:var(--down)}}
</style></head><body><div class="wrap">
<h1>Systemic + TAM — growth × risk, tracked over time{title_suffix}</h1>
<div class="meta">Model as of {html.escape(str(as_of))} · regenerated {gen} · research model, not investment advice</div>
{stress_banner}
{conc_banner}
<div class="legend">
  <span><i style="background:var(--info-t)"></i>growth, next 18m</span>
  <span><i style="background:#efeee8"></i>no &gt;25% fall</span>
  <span><i style="background:#1d9e75"></i>back ≤1y</span>
  <span><i style="background:#9fe1cb"></i>1–2y</span>
  <span><i style="background:#ef9f27"></i>2–3y</span>
  <span><i style="background:#e24b4a"></i>&gt;3y (long)</span>
  <span>▲▼ = 30-day change in the &gt;3y tail</span>
</div>
<div class="explain">
  <div class="b"><h4>Growth % — "how fast"</h4>
    <p>Forward estimate of <b>revenue growth over the next 18 months</b>; it sets the tier (high &gt;40%, moderate 15–40%, safe &lt;15%). Bigger = faster-growing, with more upside <em>and</em> usually more to lose in a panic.</p></div>
  <div class="b"><h4>Recovery bar &amp; the &gt;3y % — "how long to climb back"</h4>
    <p>Across all scenarios: the grey slice is "never fell &gt;25%"; the greens are deep falls that recovered within <b>1 / 2 / 3 years</b>; the <b>red slice is the &gt;3-year tail</b> — a deep fall that takes <em>many years</em> to heal (we can't truly say "never" — the sim only runs ~3.5y). The % shown is that red tail. For a single stock it largely reflects <b>management/execution risk</b>; a diversified ETF dilutes it.</p></div>
</div>
<details style="margin:6px 0 16px;background:#fff;border:1px solid #e7e5dd;border-radius:10px;padding:10px 14px">
  <summary style="cursor:pointer;font-weight:600;font-size:13px">How the ranking works</summary>
  <div style="font-size:12px;color:#444;line-height:1.6;margin-top:8px">
  Two axes, two sort keys — so different views can look ordered differently even though it's the same data:
  <ul style="margin:6px 0;padding-left:18px">
    <li><b>Growth</b> (expected 18-month revenue growth) sets the <b>tier</b> (&gt;40% / 15–40% / &lt;15%). The recovery-profile <b>bars are sorted by growth</b> within each tier.</li>
    <li><b>Risk</b> is <b>simulated</b>, not assigned: a regime-switching Monte Carlo where <b>beta sets how deep a name falls</b> and <b>TAM-penetration sets whether it recovers</b>. The headline is the <b>&gt;3y tail</b> (P of a &gt;25% fall still underwater at ~3.5y). Macro-stress scales the crisis odds.</li>
    <li><b>vs S&amp;P / vs SCHD</b> combine both: (growth ÷ benchmark growth) × (benchmark tail ÷ name tail). Benchmark = 1.00. <b>Sorting by this gives a different order than sorting by growth</b> — it rewards growth-per-unit-of-risk, so a lower-tail name can outrank a faster grower.</li>
  </ul>
  Not an expected-return forecast or a buy list; growth and the judgment scores are opinions the model sweeps. The vs-S&amp;P scaling is growth-tilted (it under-penalizes leveraged ETFs' fat tails — check P(&gt;25% fall) directly).
  </div>
</details>
{tiers_html}
{table_html}
{changes_html}
<div class="foot">Tiers by expected 18-month growth (&gt;40% / 15–40% / &lt;15%); ranked by growth within tier.
The recovery bar &amp; &gt;3y tail are unconditional (across all scenarios), so they're comparable across names and between stocks and ETFs.
The arrow shows the 30-day change in the &gt;3y tail. Growth figures are forward estimates; recovery figures are simulated.</div>
</div></body></html>"""

    with open(out_path, "w") as f:
        f.write(page)
    print(f"Wrote {os.path.basename(out_path)}  ({len(rows)} names shown).")
    return out_path


if __name__ == "__main__":
    build()  # full universe
    build(kind="ETF", cap=3, title_suffix=" — ETFs only (1–3 per tier)",
          out_path=os.path.join(HERE, "tier_dashboard_etf.html"),
          csv_path=os.path.join(HERE, "tier_table_etf.csv"))
