"""
============================================================================
 ETF_LENS -- the basket recovery scorecard (why an ETF is more predictable)
============================================================================
 A single stock's crash outcome is an idiosyncratic lottery: solvency, dilution,
 a lost customer, a failed product. An ETF averages that away, so the question
 shifts from "will THIS company recover?" to a more stable one:

   1. THEME DURABILITY  -- is the aggregate TAM/SAM intact after the crash, and
      is the market still growing? (TAM doesn't die in a crash; it changes hands
      among the survivors -- "conservation of TAM".)
   2. FINANCIAL RESILIENCE -- holdings-weighted balance-sheet strength: can the
      MAJORITY self-fund a recovery (the cash-rich leaders buy the dip and take
      the zombies' share)?
   3. FRAGILE-WEIGHT -- what share of the basket sits in weak-balance-sheet names
      that could permanently impair? (an ETF can look fine on average yet carry a
      dangerous tail.)
   4. CONCENTRATION -- top-1/3/5 weight, effective number of holdings, leader
      dependency. A concentrated thematic ETF still behaves like its top names.
   5. RECOVERY-WEIGHT DECOMPOSITION -- instead of "will every holding recover?",
      ask "what % of ETF WEIGHT recovers fast / slow / never?".

 Predictability class (GPT taxonomy): broad index (highest) > thematic-
 diversified > narrow-concentrated (acts like its top holdings) > leveraged
 (path-dependent, separate).

 Reads holdings weights from tam_bridge.ETF_HOLDINGS and per-name financials
 from extension_data / solvency. ESTIMATES. RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import extension_data as X
import solvency as SV

# leveraged + broad ETFs that have no per-holding map in ETF_HOLDINGS -> classify only
LEVERAGED = {"SOXL (3x Semis)", "TECL (3x Tech)", "TQQQ (3x NDX)"}
BROAD = {"VOO (S&P 500)", "QQQ (Nasdaq-100)", "SCHD (Dividend)"}   # truly broad indices
SECTOR_DIVERSIFIED = {"VGT (Info Tech)", "IGV (Software)"}          # broad-within-a-sector, mega-cap tilt
THEMATIC_NOMAP = {"DTCR (Data Ctr Infra)", "GRID (Smart Grid)", "NUKE (Nuclear/Uranium)"}  # single-theme
CONCENTRATED_NOMAP = {"ARKK (ARK Innovation)"}   # concentrated burner basket, no holdings map


def _classify(name, items):
    if name in LEVERAGED:
        return "leveraged (path-dependent — treat separately)"
    if name in BROAD:
        return "broad index (highest predictability)"
    if name in SECTOR_DIVERSIFIED:
        return "sector-diversified (mega-cap/quality tilt)"
    if name in THEMATIC_NOMAP:
        return "thematic-diversified (theme TAM/SAM is the driver)"
    if name in CONCENTRATED_NOMAP:
        return "narrow/concentrated (acts like its top holdings)"
    if not items:
        return "unmapped"
    ws = sorted((w for _, w in items), reverse=True)
    tot = sum(ws) or 1.0
    top3 = sum(ws[:3]) / tot
    neff = 1.0 / sum((w / tot) ** 2 for w in ws)
    if top3 > 0.55 or neff < 4:
        return "narrow/concentrated (acts like its top holdings)"
    return "thematic-diversified (theme TAM/SAM is the driver)"


def _is_known(h):
    """A holding the model has explicit financials for (else default-driven)."""
    return (h in getattr(X, "SOLVENCY", {})) or (h in getattr(X, "BALANCE", {}))


def scorecard(name, full):
    """5-question scorecard for an ETF. `full` is the RAW holdings dict (incl
    uncovered named holdings and the `_other_` residual). Concentration is
    reported BOTH over the whole fund and over the model-covered subset, with an
    explicit coverage/confidence flag, so the decimals aren't read as more
    precise than the data supports (GPT review)."""
    fund_tot = sum(full.values()) or 1.0
    named = [(h, w) for h, w in full.items() if not h.startswith("_")]
    other_w = sum(w for h, w in full.items() if h.startswith("_")) / fund_tot
    known = [(h, w) for h, w in named if _is_known(h)]
    unknown = [(h, w) for h, w in named if not _is_known(h)]
    known_cov = sum(w for _, w in known) / fund_tot
    unknown_w = sum(w for _, w in unknown) / fund_tot
    # concentration over the WHOLE fund (all named, true weights)
    nw = sorted((w / fund_tot for _, w in named), reverse=True)
    top3_fund = sum(nw[:3]); top5_fund = sum(nw[:5])
    # concentration + scores over the COVERED (model-scored) subset
    ctot = sum(w for _, w in known) or 1.0
    cw = sorted((w / ctot for _, w in known), reverse=True)
    top3_cov = sum(cw[:3])
    neff_cov = 1.0 / sum((w / ctot) ** 2 for _, w in known) if known else 0.0
    theme_dur = sum((w / ctot) * X.solvency_inputs(h)[2] for h, w in known) if known else 0.0
    fin_resil = sum((w / ctot) * X.balance(h) for h, w in known) if known else 0.0
    fragile_w = sum((w / ctot) for h, w in known if X.balance(h) < 0.40 or SV._stock_impairment(h) > 0.15) if known else 0.0
    perm_w = sum((w / ctot) * SV._stock_impairment(h) for h, w in known) if known else 0.0
    fast_w = sum((w / ctot) for h, w in known if X.balance(h) >= 0.70 and SV._stock_impairment(h) < 0.05) if known else 0.0
    slow_w = max(0.0, 1.0 - fast_w - perm_w)
    conf = "high" if known_cov >= 0.60 else ("medium" if known_cov >= 0.40 else "LOW — default-driven")
    return dict(known_coverage=round(known_cov, 2), unknown_named_weight=round(unknown_w, 2),
                other_weight=round(other_w, 2), confidence=conf,
                top3_fund=round(top3_fund, 2), top5_fund=round(top5_fund, 2),
                top3=round(top3_cov, 2), neff=round(neff_cov, 1),
                theme_durability=round(theme_dur, 2), fin_resilience=round(fin_resil, 2),
                fragile_weight=round(fragile_w, 2),
                fast_weight=round(fast_w, 2), slow_weight=round(slow_w, 2),
                permanent_weight=round(perm_w, 3))


def run(verbose=True):
    import calibration as C, tam_bridge as TB
    holdings = getattr(TB, "ETF_HOLDINGS", {})
    out = {}
    for etf, h in holdings.items():
        items = [(k, w) for k, w in h.items() if not k.startswith("_")]
        sc = scorecard(etf, h)                  # pass the FULL dict (incl _other_)
        sc["class"] = _classify(etf, items)
        out[etf] = sc
    # classification-only for mapless ETFs
    for etf in sorted(BROAD | SECTOR_DIVERSIFIED | THEMATIC_NOMAP | LEVERAGED | CONCENTRATED_NOMAP):
        out.setdefault(etf, {"class": _classify(etf, None)})

    if verbose:
        print("ETF RECOVERY LENS -- basket > single-name (theme + resilience, not one CEO)")
        print("=" * 92)
        mapped = [(k, v) for k, v in out.items() if "theme_durability" in v]
        mapped.sort(key=lambda kv: -kv[1]["theme_durability"])
        print(f"{'ETF':24s} {'cov':>4s} {'conf':>6s} {'themeDur':>8s} {'top3fund':>8s} {'top3cov':>7s} {'effN':>4s}  fast/slow/perm")
        print("-" * 96)
        for etf, v in mapped:
            print(f"{etf[:24]:24s} {v['known_coverage']*100:3.0f}% {v['confidence'][:6]:>6s} "
                  f"{v['theme_durability']:8.2f} {v['top3_fund']*100:7.0f}% {v['top3']*100:6.0f}% {v['neff']:4.1f}  "
                  f"{v['fast_weight']*100:3.0f}/{v['slow_weight']*100:3.0f}/{v['permanent_weight']*100:3.0f}%")
        print("\nPredictability class (all ETFs):")
        order = {"broad index (highest predictability)": 0,
                 "thematic-diversified (theme TAM/SAM is the driver)": 1,
                 "narrow/concentrated (acts like its top holdings)": 2,
                 "leveraged (path-dependent — treat separately)": 3}
        for etf, v in sorted(out.items(), key=lambda kv: order.get(kv[1]["class"], 9)):
            print(f"  {etf[:26]:26s} {v['class']}")
    json.dump(out, open(os.path.join(HERE, "etf_lens.json"), "w"), indent=1)

    # markdown
    L = ["# ETF recovery lens — the basket scorecard",
         "\n*A single stock's crash outcome is an idiosyncratic lottery; an ETF averages it "
         "away, leaving the more forecastable question: is the theme's aggregate TAM/SAM intact, "
         "and can the majority of the basket self-fund a recovery? "
         "'Conservation of TAM' — demand doesn't die in a crash, it changes hands among survivors. "
         "Research model, not investment advice.*",
         "\n| ETF | class | coverage | conf | theme dur | fin. resil | fragile wt | top-3 fund | top-3 cov | eff N | fast/slow/perm |",
         "|---|---|--:|:--:|--:|--:|--:|--:|--:|--:|---|"]
    mapped = sorted([(k, v) for k, v in out.items() if "theme_durability" in v],
                    key=lambda kv: -kv[1]["theme_durability"])
    for etf, v in mapped:
        L.append(f"| {etf} | {v['class'].split(' (')[0]} | {v['known_coverage']*100:.0f}% | {v['confidence'][:4]} | "
                 f"{v['theme_durability']:.2f} | {v['fin_resilience']:.2f} | {v['fragile_weight']*100:.0f}% | "
                 f"{v['top3_fund']*100:.0f}% | {v['top3']*100:.0f}% | {v['neff']:.1f} | "
                 f"{v['fast_weight']*100:.0f}/{v['slow_weight']*100:.0f}/{v['permanent_weight']*100:.0f}% |")
    L.append("\n## Predictability class (GPT taxonomy)")
    for cls in ["broad index", "thematic-diversified", "narrow/concentrated", "leveraged"]:
        names = [e for e, v in out.items() if v["class"].startswith(cls)]
        if names:
            L.append(f"- **{cls}**: {', '.join(sorted(names))}")
    L.append("\n## How to read it")
    L.append("- **theme durability / fin. resilience**: holdings-weighted; higher = the basket's "
             "market and balance sheets bridge a crash.")
    L.append("- **fragile wt**: share of the basket in weak-balance-sheet names — the dangerous tail "
             "an average can hide.")
    L.append("- **top-3 / eff. N**: concentration. A high top-3 or low effective-N means the ETF "
             "still behaves like its lead holdings (the `correlation.py` ~0.95 lead-correlation warning).")
    L.append("- **fast/slow/perm weight**: instead of forecasting every holding, the share of basket "
             "weight expected to recover fast, slowly, or impair permanently.")
    L.append("- **coverage / conf**: share of the fund in holdings the model scores explicitly. "
             "theme/resilience/fragile and top-3-cov are over that COVERED subset; **top-3 fund** is "
             "over the whole fund. LOW confidence (coverage <40%) means the decimals are default-driven "
             "and only the class is reliable (e.g. DRAM, QTUM, AIQ).")
    open(os.path.join(HERE, "etf_lens.md"), "w").write("\n".join(L))
    if verbose:
        print("\nwrote etf_lens.md / .json")
    return out


if __name__ == "__main__":
    run()
