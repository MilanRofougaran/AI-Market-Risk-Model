"""
============================================================================
 TIERING  --  systemic_model
============================================================================
 Presentation layer: organize the universe into THREE GROWTH TIERS and show,
 for each name, its expected growth AND its downside risk side by side, ranked
 by growth within each tier.

 The unit is the SUBGROUP: each theme is represented by its ETF (the diversified
 basket) and its single best representative stock (the pure-play). An ETF and
 its stock can land in different tiers -- that is informative: the basket damps
 both the growth and the risk of the pure-play.

   TIER 1  HIGH growth        expected 18m revenue growth  > 40%
   TIER 2  MODERATE growth    15% - 40%
   TIER 3  SAFE / smaller     < 15%

 Within each tier, names are ranked by expected growth (highest first), with
 the permanent-loss risk shown alongside so the growth/safety trade-off is
 visible at a glance.

 GROWTH numbers are forward 18-month revenue-growth expectations [JUDGMENT,
 research-informed, Jun 2026]. RISK numbers are read live from results.json
 (run the model first). Leveraged vehicles (TECL) are excluded from the tiers
 and reported separately, because their risk is volatility decay, not a view
 on fundamentals.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
#  THE TIERABLE UNIVERSE  --  every name we rank, with its kind, theme, and
#  forward 18-month revenue-growth expectation (decimal) [JUDGMENT, Jun 2026].
#  ETFs are subgroups/baskets; stocks are the pure-plays. Edit growth freely.
#  Risk for each is read live from results.json (run the model first).
# ---------------------------------------------------------------------------
UNIVERSE = {
    # name                         (kind,   theme,                 exp_growth_18m)
    "IonQ":                        ("stock", "Quantum",              0.80),
    "Astera Labs":                 ("stock", "AI connectivity",      0.70),
    "CoreWeave":                   ("stock", "AI cloud (GPU)",       0.60),
    "Palantir":                    ("stock", "Gen-AI software",      0.55),
    "Lumentum":                    ("stock", "AI optical",           0.55),
    "Applied Optoelectronics":     ("stock", "AI optical",           0.55),
    "Micron":                      ("stock", "Memory / HBM",         0.50),
    "AMD":                         ("stock", "AI compute",           0.45),
    "NVIDIA":                      ("stock", "Gen-AI infra",         0.45),
    "DRAM (Roundhill Memory)":     ("ETF",   "Memory / HBM",         0.45),
    "Broadcom":                    ("stock", "AI compute",           0.38),
    "Marvell":                     ("stock", "AI compute",           0.35),
    "CHAT (Roundhill GenAI)":      ("ETF",   "Generative AI",        0.32),
    "AppLovin":                    ("stock", "AI ad-tech",           0.30),
    "SMH (VanEck Semis)":          ("ETF",   "Semis (broad)",        0.30),
    "Vertiv":                      ("stock", "AI power / cooling",   0.28),
    "SOXX (iShares Semis)":        ("ETF",   "Semis (broad)",        0.28),
    "Coherent":                    ("stock", "AI optical",           0.25),
    "ARM":                         ("stock", "Chip IP / licensing",  0.25),
    "AIQ (Global X AI)":           ("ETF",   "AI broad",             0.25),
    "QTUM (Defiance Quantum)":     ("ETF",   "Quantum",              0.22),
    "Meta":                        ("stock", "Megacap / ads",        0.18),
    "Oracle":                      ("stock", "Enterprise cloud",     0.16),
    "Microsoft":                   ("stock", "AI cloud",             0.14),
    "Texas Instruments":           ("stock", "Analog / industrial",  0.14),
    "Amazon":                      ("stock", "Cloud / retail",       0.13),
    "Alphabet":                    ("stock", "Ads / cloud / AI",     0.12),
    "Qualcomm":                    ("stock", "Edge AI / mobile",     0.08),
    "Apple":                       ("stock", "Devices / services",   0.07),
    "Cisco":                       ("stock", "Networking",           0.06),
    "IBM":                         ("stock", "Hybrid cloud / AI",    0.05),
    "Kioxia":                      ("stock", "NAND memory",          0.05),
    # broad / thematic ETFs (for the ETF-only view; direct-spec in tam_bridge):
    "Tesla":                       ("stock", "EV / robotaxi / AI",   0.17),
    "ARKK (ARK Innovation)":       ("ETF",   "Disruptive (Tesla-led)", 0.42),
    "QQQ (Nasdaq-100)":            ("ETF",   "Mega-cap tech",        0.16),
    "VOO (S&P 500)":               ("ETF",   "Broad US market",      0.09),
    "SCHD (Dividend)":             ("ETF",   "Quality dividend",     0.06),
    # data-center power / grid / cooling / infra + popular broad ETFs
    "NUKE (Nuclear/Uranium)":      ("ETF",   "Nuclear power",        0.22),
    "IGV (Software)":              ("ETF",   "Software",             0.20),
    "GRID (Smart Grid)":           ("ETF",   "Grid / power",         0.18),
    "VGT (Info Tech)":             ("ETF",   "Info tech (broad)",    0.15),
    "DTCR (Data Ctr Infra)":       ("ETF",   "Data-center infra",    0.14),
    # leveraged (3x daily reset) — injected via add_leveraged.py
    "SOXL (3x Semis)":             ("ETF",   "Semis 3x leveraged",   0.60),
    "TECL (3x Tech)":              ("ETF",   "Tech 3x leveraged",    0.50),
    "TQQQ (3x NDX)":               ("ETF",   "Nasdaq 3x leveraged",  0.45),
}

# Leveraged trading vehicles -- excluded from the growth tiers, flagged apart.
LEVERAGED = ["SOXL (3x Semis)", "TECL (3x Tech)", "TQQQ (3x NDX)"]
# (bug fixed: list previously held only a case-mismatched "TECL (3x tech)", so
#  all three leveraged vehicles leaked into the growth tiers. They are trading
#  instruments with path-dependent volatility decay -- NOT comparable holdings.)

TIERS = [
    ("TIER 1  ·  HIGH growth (>40% expected, 18m)",     0.40, 2.00),
    ("TIER 2  ·  MODERATE growth (15-40%)",             0.15, 0.40),
    ("TIER 3  ·  SAFE / smaller growth (<15%)",        -1.00, 0.15),
]


def _load_results(path=None):
    path = path or os.path.join(HERE, "results.json")
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
#  PERMANENCE  --  P(a deep drawdown is TRULY permanent | still underwater at
#  the end of the ~3.5y sim). The sim's "never recovers" is really "not back
#  in 3.5y"; a broad index mean-reverts and essentially always heals given
#  time, while a single speculative stock can genuinely die. We scale the tail
#  by this so the index's permanent risk collapses toward ~0 and speculative
#  single names keep theirs. [JUDGMENT, editable]
#    broad index ~0.05  ·  sector ETF ~0.18  ·  mega-cap ~0.32  ·
#    cyclical single ~0.55  ·  speculative single ~0.8
# ---------------------------------------------------------------------------
PERMANENCE = {
    # broad / diversified ETFs — the market heals; permanent loss ~ nil
    "VOO (S&P 500)": 0.05, "SCHD (Dividend)": 0.05, "QQQ (Nasdaq-100)": 0.08,
    "SMH (VanEck Semis)": 0.18, "SOXX (iShares Semis)": 0.18,
    "AIQ (Global X AI)": 0.18, "CHAT (Roundhill GenAI)": 0.20,
    "DRAM (Roundhill Memory)": 0.25, "QTUM (Defiance Quantum)": 0.25,
    "ARKK (ARK Innovation)": 0.35,
    "DTCR (Data Ctr Infra)": 0.15, "VGT (Info Tech)": 0.12, "GRID (Smart Grid)": 0.22,
    "IGV (Software)": 0.20, "NUKE (Nuclear/Uranium)": 0.30,
    "SOXL (3x Semis)": 0.55, "TECL (3x Tech)": 0.55, "TQQQ (3x NDX)": 0.55,
    # mega-cap durable single names — dominant franchises rarely die outright
    "Microsoft": 0.30, "Apple": 0.30, "Alphabet": 0.30, "Amazon": 0.32,
    "Meta": 0.32, "NVIDIA": 0.35, "Broadcom": 0.38,
    # quality / mid single names
    "Texas Instruments": 0.38, "Qualcomm": 0.40, "Cisco": 0.40, "IBM": 0.42,
    "Oracle": 0.42, "AMD": 0.45, "ARM": 0.45, "Marvell": 0.48, "Vertiv": 0.50,
    # cyclical / contested single names
    "Micron": 0.55, "Lumentum": 0.55, "Coherent": 0.55, "Kioxia": 0.60,
    "Applied Optoelectronics": 0.65,
    # speculative / narrative single names — genuine permanent-failure risk
    "Palantir": 0.60, "AppLovin": 0.60, "Tesla": 0.65, "Astera Labs": 0.65,
    "CoreWeave": 0.80, "IonQ": 0.85,
}
DEFAULT_PERMANENCE = 0.50


def _risk(results, name):
    """Return (p_deep_permanent, p_recover_18m, p_dd25) for a modeled name, or
    None if it is not in the company results."""
    rc = results["companies"]["recovery_cond"].get(name)
    if not rc:
        return None
    return (rc.get("p_deep_permanent"), rc.get("p_recover"), rc.get("p_dd25"))


def _curve_at(results, name, months):
    rc = results["companies"]["recovery_cond"].get(name, {})
    for pt in rc.get("recovery_curve", []) or []:
        if pt["months"] == months:
            return pt["p_recovered"]
    return None


def build_rows(results):
    """Assemble (name, kind, theme, growth, risk...) for every tierable name."""
    rows = []

    def add(name, kind, theme, growth):
        r = _risk(results, name)
        if r is None:
            return  # not modeled (skip silently; reported in gaps elsewhere)
        pdp, prec, pdd = r
        # risk-adjusted ratios (reward per unit of risk; higher = better):
        #   g_per_tail = growth / permanent-loss tail  (growth per unit of "never recovers")
        #   g_per_fall = growth / P(>25% fall)         (growth per unit of drawdown odds)
        g_per_tail = growth / pdp if (pdp and pdp > 1e-6) else None
        g_per_fall = growth / pdd if (pdd and pdd > 1e-6) else None
        # TRUE permanent loss = "still underwater at 3.5y" x permanence (the
        # share that is genuinely terminal). An index heals -> ~0; a speculative
        # single name keeps most of it. The growth-per-TRUE-permanent ratio is
        # the one that treats VOO as "growth, recovers anyway".
        perm = PERMANENCE.get(name, DEFAULT_PERMANENCE)
        true_perm = (pdp or 0.0) * perm
        g_per_trueperm = growth / true_perm if true_perm > 1e-6 else None
        rows.append(dict(name=name, kind=kind, theme=theme, growth=growth,
                         p_deep_permanent=pdp, p_recover_18m=prec, p_dd25=pdd,
                         p_recover_24m=_curve_at(results, name, 24),
                         permanence=perm, true_perm=true_perm,
                         g_per_tail=g_per_tail, g_per_fall=g_per_fall,
                         g_per_trueperm=g_per_trueperm))

    for name, (kind, theme, growth) in UNIVERSE.items():
        add(name, kind, theme, growth)

    # ---- benchmark each name's permanent risk against the S&P (VOO) ----
    # perm_vs_sp = stock true-permanent loss / S&P true-permanent loss (a
    # MULTIPLE: "this name carries N times the permanent risk of just holding
    # the index"). g_adj_sp = growth / perm_vs_sp -> for the S&P this is just
    # its growth; a name with 2x the S&P's permanent risk has its growth halved.
    # Benchmarks use the RAW >3y tail (still-underwater-at-3.5y), per the
    # formula: reward = (growth / bench growth) x (bench tail / name tail).
    # Benchmark itself = 1.00.
    def _bench(name, default_g, default_t):
        b = next((r for r in rows if r["name"] == name), None)
        gp = b["growth"] if (b and b["growth"] > 1e-6) else default_g
        tt = b["p_deep_permanent"] if (b and b["p_deep_permanent"] > 1e-6) else default_t
        return gp, tt
    sp_growth, sp_tail = _bench("VOO (S&P 500)", 0.09, 0.21)
    sc_growth, sc_tail = _bench("SCHD (Dividend)", 0.06, 0.19)

    def _norm(g, tail, bg, bt):
        if tail <= 1e-6 or bg <= 1e-6:
            return None
        return (g / bg) * (bt / tail)
    for r in rows:
        tail = r["p_deep_permanent"] or 0.0
        r["perm_vs_sp"] = (tail / sp_tail) if sp_tail > 1e-6 else None   # raw-tail risk multiple
        r["vs_sp"] = _norm(r["growth"], tail, sp_growth, sp_tail)        # S&P = 1.00
        r["vs_schd"] = _norm(r["growth"], tail, sc_growth, sc_tail)      # SCHD = 1.00
    return rows


def tier_rows(rows):
    """Bucket rows into the growth tiers; sort each tier by growth desc."""
    out = []
    for label, lo, hi in TIERS:
        members = [r for r in rows
                   if lo < r["growth"] <= hi and r["name"] not in LEVERAGED]
        members.sort(key=lambda r: -r["growth"])
        out.append((label, members))
    lev = leveraged_rows(rows)
    if lev:
        out.append(("Trading vehicles — 3x leveraged (volatility decay; excluded from tiers & rankings)", lev))
    return out


def bucket(r):
    """Coarse verdict bucket (review feedback: present buckets, not decimals)."""
    if r["name"] in LEVERAGED:
        return "trading-vehicle"
    t = r.get("p_deep_permanent")
    if t is None or t != t:
        return "n/a"
    return "robust" if t <= 0.22 else ("watch" if t <= 0.27 else "fragile")


def leveraged_rows(rows):
    """The 3x vehicles, separated: trading instruments, not growth holdings."""
    return [r for r in rows if r["name"] in LEVERAGED]


def _pct(x):
    return f"{x*100:.0f}%" if (x is not None and x == x) else "n/a"


def print_tiers(results):
    rows = build_rows(results)
    tiers = tier_rows(rows)
    print("#" * 78)
    print("#  GROWTH-TIERED RANKING   (growth first, risk alongside)")
    print(f"#  model as of {results.get('as_of')}   ·   RESEARCH MODEL, NOT ADVICE")
    print("#" * 78)
    for label, members in tiers:
        print(f"\n{label}")
        print("-" * 78)
        if not members:
            print("  (none)")
            continue
        print(f"  {'Name':26s} {'Type':5s} {'Theme':18s} {'Growth':>7s} "
              f"{'Risk(perm)':>10s} {'Rec18m':>7s}")
        for r in members:
            print(f"  {r['name']:26s} {r['kind']:5s} {r['theme']:18s} "
                  f"{_pct(r['growth']):>7s} {_pct(r['p_deep_permanent']):>10s} "
                  f"{_pct(r['p_recover_18m']):>7s}")
    # leveraged vehicles, separately
    print("\nEXCLUDED  ·  leveraged vehicles (risk = volatility decay, not a view)")
    print("-" * 78)
    for nm in LEVERAGED:
        ex = results["exposures"].get(nm, {}).get("18m", {}).get("exceedance")
        thr = results.get("thresholds", [])
        if ex and thr:
            parts = " ".join(f">{int(t*100)}%={v*100:.0f}%" for t, v in zip(thr, ex))
            print(f"  {nm:18s} 18m drawdown odds: {parts}")
    print()
    return tiers


def write_markdown(results, path=None):
    path = path or os.path.join(HERE, "tiered_ranking.md")
    rows = build_rows(results)
    tiers = tier_rows(rows)
    L = []
    L.append("# Growth-tiered ranking — ETFs (subgroups) + top stock per theme")
    L.append("")
    L.append(f"*Model calibrated {results.get('as_of')} · ranked by expected "
             f"18-month growth, with downside risk shown alongside.*")
    L.append("")
    L.append("**Research model, not investment advice.** Growth figures are "
             "forward expectations (judgment); risk figures are simulated. "
             "`Risk(perm)` = P(a >25% drawdown that never recovers) — lower is "
             "safer. `Rec 18m` / `Rec 24m` = P(recovered by that horizon | fell >25%).")
    L.append("")
    for label, members in tiers:
        L.append(f"## {label}")
        L.append("")
        if not members:
            L.append("_(none in this tier)_")
            L.append("")
            continue
        L.append("| Rank | Name | Type | Theme | Exp. growth (18m) | Risk (perm) | Rec 18m | Rec 24m |")
        L.append("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(members, 1):
            L.append(f"| {i} | {r['name']} | {r['kind']} | {r['theme']} "
                     f"| {_pct(r['growth'])} | {_pct(r['p_deep_permanent'])} "
                     f"| {_pct(r['p_recover_18m'])} | {_pct(r['p_recover_24m'])} |")
        L.append("")
    # leveraged note
    L.append("## Excluded — leveraged vehicles")
    L.append("")
    for nm in LEVERAGED:
        ex = results["exposures"].get(nm, {}).get("18m", {}).get("exceedance")
        thr = results.get("thresholds", [])
        if ex and thr:
            parts = ", ".join(f">{int(t*100)}% = {v*100:.0f}%" for t, v in zip(thr, ex))
            L.append(f"- **{nm}** — a 3× daily-reset vehicle, not a growth holding. "
                     f"18-month drawdown odds: {parts}. The risk is volatility "
                     f"decay, independent of any fundamental view.")
    L.append("")
    with open(path, "w") as f:
        f.write("\n".join(L))
    return path


if __name__ == "__main__":
    res = _load_results()
    tiers = print_tiers(res)
    p = write_markdown(res)
    print(f"Saved {os.path.basename(p)}")
