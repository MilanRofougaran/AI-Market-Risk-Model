"""
============================================================================
 SCREEN_RULES  --  systemic_model / discovery
============================================================================
 THE SCORING LOGIC for the discovery stage. This module is deliberately
 SEPARATE from the agent and the registry so that the RULE by which candidates
 are ranked is explicit, auditable, and editable on its own. When a name ranks
 high, you can read this file and see exactly why -- nothing is hidden inside
 an opaque score.

 THE RANKING PHILOSOPHY (the choice you made: a BLEND).
 "Highest growth" is judged on a blend of:
     (1) DEMONSTRATED growth  -- recent realized revenue / earnings growth.
         This is evidence the forward story is REAL, not just a narrative.
     (2) FORWARD potential     -- TAM size, TAM growth rate, and how much
         runway remains (low penetration = long runway).
 We blend them because demonstrated execution is what separates an earned
 growth premium from a floating one -- the same distinction the whole model
 is built on. A name with a huge TAM but no delivery is a story; a name
 compounding fast AND with runway left is the real thing.

 Two penalties keep the blend honest:
     - SATURATION penalty : high penetration shrinks forward potential
       (you cannot grow into a market you already own).
     - QUALITY/HYPE penalty: soft TAMs, single-source claims, and pure-
       narrative names are discounted (ties into the red-team filter).

 Every weight below is a stated parameter you can tune. The defaults encode
 "blend with a modest tilt toward demonstrated execution," which is the
 conservative reading of your instruction.
============================================================================
"""

# ---- tunable weights (sum of the two growth weights = 1.0) ----
W_DEMONSTRATED = 0.55     # weight on realized recent growth (the "is it real" signal)
W_FORWARD      = 0.45     # weight on forward runway/TAM potential
SATURATION_PENALTY = 0.30 # how hard high penetration discounts forward potential
QUALITY_FLOOR  = 0.40     # minimum multiplier a low-quality/soft-TAM name keeps

# normalization anchors (so raw inputs map onto a 0-1 scale sensibly)
GROWTH_CAP = 1.00         # 100% YoY revenue growth maps to the top of the scale
TAM_CAGR_CAP = 0.60       # a 60%/yr TAM growth maps to the top


def _clip01(x):
    return max(0.0, min(1.0, x))


def score_candidate(c):
    """Score one candidate dict on the blended rule. Returns the candidate with
    score components attached, so the ranking is fully explainable.

    Expected fields in c (any missing field is treated conservatively):
      demonstrated_growth : recent YoY revenue growth (decimal, e.g. 0.66)
      tam_cagr            : growth rate of its addressable market (decimal)
      penetration         : current revenue / TAM (decimal, 0-1)
      tam_quality         : TAM credibility 0-1 (soft aggregate -> low)
      conviction          : analyst/source conviction 0-1 (hype -> low)
    """
    g  = _clip01(c.get("demonstrated_growth", 0.0) / GROWTH_CAP)
    cg = _clip01(c.get("tam_cagr", 0.0) / TAM_CAGR_CAP)
    pen = _clip01(c.get("penetration", 0.5))
    q  = _clip01(c.get("tam_quality", 0.6))
    conv = _clip01(c.get("conviction", 0.6))

    # forward potential = how fast the ceiling rises, discounted by how much of
    # the room is already used up (saturation penalty)
    forward = cg * (1.0 - SATURATION_PENALTY * pen)

    # blended raw growth score
    raw = W_DEMONSTRATED * g + W_FORWARD * forward

    # quality / hype multiplier: soft TAMs and low-conviction names are
    # discounted but never zeroed (they may still be worth a look)
    quality_mult = QUALITY_FLOOR + (1 - QUALITY_FLOOR) * (0.5 * q + 0.5 * conv)

    score = raw * quality_mult
    c = dict(c)
    c["_score_components"] = dict(
        demonstrated=round(g, 3), forward=round(forward, 3),
        blended_raw=round(raw, 3), quality_mult=round(quality_mult, 3),
    )
    c["score"] = round(score, 4)
    return c


def rank(candidates, kind=None):
    """Score and rank a list of candidates (optionally filtered to 'etf' or
    'stock'), highest score first."""
    scored = [score_candidate(c) for c in candidates
              if kind is None or c.get("kind") == kind]
    return sorted(scored, key=lambda c: -c["score"])


def select_shortlist(candidates, n_etfs=(3, 5), n_stocks=(6, 8)):
    """Apply the output-size targets: top N ETFs and top M stocks by score.
    Returns (etfs, stocks), each already ranked. Uses the UPPER bound of each
    target range so the human checkpoint has the full set to narrow from."""
    etfs   = rank(candidates, kind="etf")[: n_etfs[1]]
    stocks = rank(candidates, kind="stock")[: n_stocks[1]]
    return etfs, stocks


def explain(c):
    """One-line human-readable justification for a candidate's score."""
    sc = c["_score_components"]
    return (f"{c['name']:14s} score={c['score']:.3f}  "
            f"[demo {sc['demonstrated']:.2f} x{W_DEMONSTRATED} + "
            f"fwd {sc['forward']:.2f} x{W_FORWARD}] x quality {sc['quality_mult']:.2f}")


if __name__ == "__main__":
    # Self-test on a few illustrative (NOT real) candidates to show the rule
    # behaves sensibly: a proven fast-grower with runway should beat both a
    # saturated giant and a pure-hype story.
    demo = [
        dict(name="ProvenGrower", kind="stock", demonstrated_growth=0.60,
             tam_cagr=0.45, penetration=0.10, tam_quality=0.85, conviction=0.85),
        dict(name="SaturatedGiant", kind="stock", demonstrated_growth=0.30,
             tam_cagr=0.45, penetration=0.40, tam_quality=0.90, conviction=0.90),
        dict(name="HypeStory", kind="stock", demonstrated_growth=0.05,
             tam_cagr=0.55, penetration=0.02, tam_quality=0.30, conviction=0.25),
        dict(name="BroadETF", kind="etf", demonstrated_growth=0.35,
             tam_cagr=0.30, penetration=0.44, tam_quality=0.80, conviction=0.80),
    ]
    print("Screen-rule self-test (illustrative data):")
    for c in rank(demo):
        print("  " + explain(c))
    print("\nThe proven grower with runway should rank highest; the hype story "
          "should rank low despite a big TAM. If that holds, the rule works.")
