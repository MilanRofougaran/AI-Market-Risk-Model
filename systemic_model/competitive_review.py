"""
competitive_review.py -- audit trail + sensitivity for the competitive inputs.
Generates competitive_assumptions.md: one row per name (moat, pricing power, structural
share, company growth g, market growth m, RATIONALE, confidence) plus a moat +/-0.15
sensitivity showing how justified premium and fragility move. "moat" is the most dangerous
knob in the model -- this file exists so it is documented and stress-tested, never silent.

RATIONALES BELOW ARE PLACEHOLDER JUDGMENTS -- REVIEW / OVERWRITE. RESEARCH MODEL, NOT ADVICE.
"""
import copy, sys
import calibration as C
import engine as E

RATIONALE = {  # PLACEHOLDER -- confirm or replace per name
 "NVIDIA":     ("high",   "CUDA/ecosystem lock-in; ~80-85% AI-accelerator share; ~75% GM = real pricing power."),
 "Micron":     ("high",   "Commodity DRAM/NAND oligopoly (Samsung/SK Hynix/Micron); ASPs collapse in gluts; ~no pricing power."),
 "AMD":        ("medium", "Credible #2 CPU/GPU; gains share partly on price/value vs Intel & NVDA; margin-constrained."),
 "Broadcom":   ("medium", "Diversified franchises (networking, custom silicon); sticky designs; decent pricing."),
 "Qualcomm":   ("medium", "Modem + licensing strength, maturing handset TAM; some IP pricing power."),
 "Kioxia":     ("high",   "NAND commodity; weak pricing power; cyclical."),
 "Marvell":    ("medium", "Custom silicon / optical; gaining share; moderate, contestable moat."),
 "ARM":        ("medium", "Architecture-licensing near-monopoly; royalty pricing power; but very rich multiple."),
 "Palantir":   ("low",    "Differentiated platform (Foundry/Gotham); few direct comps; sticky; decent pricing; high multiple."),
 "Astera Labs":("low",    "Connectivity leader (retimers/CXL) early; real but contestable; moderate moat; MC-uncertain."),
 "CoreWeave":  ("low",    "GPU cloud, capacity-driven; low switching costs; price-competitive; balance-sheet/survivability risk."),
}

def _decomp_one(nm, moat_override=None):
    comp = copy.deepcopy(getattr(C, "COMPETITIVE", {}))
    if moat_override is not None and nm in comp:
        comp[nm]["moat"] = max(0.0, min(1.0, moat_override))
    saved = C.COMPETITIVE; C.COMPETITIVE = comp
    try:
        if nm in C.COMPANIES:
            o = E.decompose_premium()[nm]
        else:
            sys.path.insert(0, "discovery"); import tam_bridge as TB
            inp = dict(TB.STOCK_TAM_FACTS[nm]); inp["name"] = nm
            o = E.decompose_premium({nm: inp})[nm]
    finally:
        C.COMPETITIVE = saved
    return o["justified_pts"], o["fragility"]

def build():
    L = ["# Competitive assumptions — review table & moat sensitivity", "",
         "**These are research judgments, not engine outputs. Review/overwrite per name.** "
         "moat is the most dangerous knob: a generous moat hallucinates safety. Keep conservative, "
         "document, and never let it override the survivability gate. RESEARCH MODEL — NOT ADVICE.", "",
         "| Name | moat | pricing | struct_share | g | m | conf | rationale (REVIEW) |",
         "|---|---|---|---|---|---|---|---|"]
    comp = getattr(C, "COMPETITIVE", {})
    for nm, d in comp.items():
        conf, why = RATIONALE.get(nm, ("?", "—"))
        L.append(f"| {nm} | {d['moat']:.2f} | {d['pricing_power']:.2f} | {d['struct_share']:.2f} | "
                 f"{d['g']:.0%} | {d['m']:.0%} | {conf} | {why} |")
    L += ["", "## Moat sensitivity (±0.15): justified premium pts & fragility",
          "If fragility swings hard on a 0.15 moat tweak, the name's safety is moat-driven — treat with skepticism.", "",
          "| Name | moat−0.15 | base | moat+0.15 | justified pts (−/base/+) | fragility (−/base/+) |",
          "|---|---|---|---|---|---|"]
    for nm, d in comp.items():
        m0 = d["moat"]
        jl, fl = _decomp_one(nm, m0 - 0.15)
        jb, fb = _decomp_one(nm, None)
        jh, fh = _decomp_one(nm, m0 + 0.15)
        L.append(f"| {nm} | {max(0,m0-0.15):.2f} | {m0:.2f} | {min(1,m0+0.15):.2f} | "
                 f"{jl:.1f} / {jb:.1f} / {jh:.1f} | {fl:.2f} / {fb:.2f} / {fh:.2f} |")
    open("competitive_assumptions.md", "w").write("\n".join(L))
    print("wrote competitive_assumptions.md")

if __name__ == "__main__":
    build()
