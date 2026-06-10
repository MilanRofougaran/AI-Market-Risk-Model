"""
============================================================================
 EXTENSION_DATA -- SAM (serviceable market) + short interest per name
============================================================================
 Adds the two inputs the base model lacked:

 sam_frac : SAM as a fraction of the headline TAM -- the part of the TAM the
            company can actually serve in the NEXT 2-3 YEARS with today's
            products, channels and capacity. TAM is the long-run ceiling;
            SAM is what near-term revenue (and hence near-term valuation)
            should be priced against. Far-future TAMs (quantum, full
            autonomy) get small fractions; mature markets get large ones.

 si       : short interest as a fraction of float (crowding/positioning).
            High SI amplifies CRISIS drawdown depth (forced unwinds, margin
            calls hitting the most-shorted, most-crowded names) and gives a
            small early-recovery kick (short covering).

 *** ALL VALUES ARE ANALYST ESTIMATES (as of June 2026) -- refresh them the
 same way calibration.MACRO is refreshed. They are swept in sensitivity. ***

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""

# name -> (sam_frac of TAM, short_interest fraction of float)
STOCK_EXT = {
    "IonQ":                    (0.04, 0.20),   # quantum TAM is ~2035; serviceable today is tiny; heavily shorted
    "Astera Labs":             (0.35, 0.05),
    "CoreWeave":               (0.45, 0.08),   # GPU-cloud demand real now, but contracts/capacity bound
    "Palantir":                (0.30, 0.04),
    "Lumentum":                (0.50, 0.04),
    "Applied Optoelectronics": (0.35, 0.15),   # crowded short
    "Micron":                  (0.65, 0.025),  # HBM demand is current
    "AMD":                     (0.55, 0.025),
    "NVIDIA":                  (0.60, 0.010),
    "Broadcom":                (0.60, 0.015),
    "Marvell":                 (0.55, 0.020),
    "AppLovin":                (0.50, 0.070),
    "Vertiv":                  (0.60, 0.030),
    "Coherent":                (0.50, 0.030),
    "ARM":                     (0.55, 0.030),
    "Meta":                    (0.75, 0.010),
    "Oracle":                  (0.70, 0.012),
    "Microsoft":               (0.75, 0.007),
    "Texas Instruments":       (0.85, 0.020),
    "Amazon":                  (0.75, 0.008),
    "Alphabet":                (0.80, 0.008),
    "Qualcomm":                (0.80, 0.015),
    "Apple":                   (0.90, 0.007),
    "Cisco":                   (0.90, 0.012),
    "IBM":                     (0.85, 0.020),
    "Kioxia":                  (0.65, 0.030),
    "Tesla":                   (0.35, 0.030),  # priced partly on robotaxi/FSD TAM that is not serviceable yet
}

# ETF-level short interest ADD-ON (sector ETFs are shorted as hedges, which
# actually CUSHIONS crisis depth a little -- hedging flow, not crowded longs).
ETF_HEDGE_SI = {"SMH": 0.03, "SOXX": 0.04, "QQQ": 0.02, "SPY": 0.02, "VOO": 0.01}

DEFAULTS = (0.60, 0.02)   # for any name without an entry


def get(name):
    """(sam_frac, si) for a stock by loose name match."""
    base = name.split(" (")[0].strip()
    for k, v in STOCK_EXT.items():
        if k.lower() == base.lower():
            return v
    return DEFAULTS


def crowd_score(si):
    """0..1 crowding score: 2% SI is normal, 17%+ is a crowded short."""
    return max(0.0, min(1.0, (si - 0.02) / 0.15))


# ---------------------------------------------------------------------------
# BALANCE-SHEET STRENGTH (0..1): net cash, FCF, buyback capacity.
# Why it matters in THIS market (2026 != 2000/2008): companies are profitable
# and cash-rich, so a drawdown is rarely an existential event -- strong
# balance sheets do NOT prevent the fall (multiple compression ignores cash),
# they power the RECOVERY (buybacks at the low, no dilution, no covenant
# stress). So this feeds recovery speed and trims the PERMANENT tail only.
# ESTIMATES (Jun 2026): 0.9+ = fortress net cash; ~0.5 = neutral;
# <0.3 = leveraged (LBO debt, GPU-backed loans, acquisition debt).
# ---------------------------------------------------------------------------
BALANCE = {
    "NVIDIA": 0.95, "Alphabet": 0.95, "Microsoft": 0.90, "Meta": 0.90,
    "Apple": 0.90,            # less net cash than peak, but buyback machine
    "Palantir": 0.85, "Tesla": 0.80, "ARM": 0.80, "Astera Labs": 0.80,
    "Amazon": 0.75, "Qualcomm": 0.70, "Cisco": 0.70, "AMD": 0.70,
    "Texas Instruments": 0.65, "Micron": 0.60, "Marvell": 0.55, "Vertiv": 0.55,
    "AppLovin": 0.50, "IonQ": 0.50,   # cash from raises, but burning it
    "Broadcom": 0.45,         # VMware acquisition debt (servicing fine)
    "Lumentum": 0.45, "IBM": 0.40, "Oracle": 0.35,   # capex debt building
    "Coherent": 0.35, "Kioxia": 0.30,                 # LBO legacy debt
    "Samsung": 0.85, "SK Hynix": 0.55,                # Samsung fortress; SK Hynix mid
    "Applied Optoelectronics": 0.25,
    "CoreWeave": 0.15,        # GPU-collateralized loans -- the one true 2008-style balance sheet here
}
BALANCE_DEFAULT = 0.55


def balance(name):
    base = name.split(" (")[0].strip()
    for k, v in BALANCE.items():
        if k.lower() == base.lower():
            return v
    return BALANCE_DEFAULT


# ---------------------------------------------------------------------------
# NET CASH as a fraction of market cap (for the trough-buyback "slingshot").
# The 0-1 BALANCE score can't express "50% vs 80% of cash" quantitatively, so
# the buyback float-cut math needs a real number. ESTIMATES (Jun 2026):
# fortress mega-caps ~6-12% of mcap in net cash; debt-funded names ~0 or negative.
# ---------------------------------------------------------------------------
NET_CASH_TO_MCAP = {
    "Apple": 0.04, "Microsoft": 0.05, "Alphabet": 0.10, "Meta": 0.07,
    "NVIDIA": 0.04, "Amazon": 0.03, "Qualcomm": 0.06, "Cisco": 0.07,
    "Texas Instruments": 0.02, "AMD": 0.05, "Marvell": 0.01, "ARM": 0.04,
    "Palantir": 0.06, "Astera Labs": 0.05, "AppLovin": 0.01,
    "Micron": 0.02, "Vertiv": 0.01, "Tesla": 0.06, "IBM": -0.05,
    "Broadcom": -0.08, "Oracle": -0.10, "Lumentum": 0.0, "Coherent": -0.05,
    "Kioxia": -0.08, "Applied Optoelectronics": 0.0, "IonQ": 0.08, "CoreWeave": -0.20,
    "Samsung": 0.12, "SK Hynix": 0.02,
}
NET_CASH_DEFAULT = 0.0


def net_cash(name):
    base = name.split(" (")[0].strip()
    for k, v in NET_CASH_TO_MCAP.items():
        if k.lower() == base.lower():
            return v
    return NET_CASH_DEFAULT


# ---------------------------------------------------------------------------
# SOLVENCY INPUTS (for the financing/impairment channel).
# The user's thesis: a high-growth name with weak financials recovers fine IF
# revenue keeps compounding through the crash (it can refinance / raise on the
# strength of the growth), but becomes a PERMANENT impairment if revenue ALSO
# craters (dilution death-spiral, covenant/refinancing distress, bankruptcy).
# Three per-name estimates (0..1), refreshed like the rest:
#   funding_need   0 = strongly FCF-positive/self-funding ; 1 = burning cash, must raise
#   debt_load      0 = net cash / no leverage             ; 1 = heavy debt, refinance risk
#   rev_durability 0 = revenue collapses in a downturn (cyclical/discretionary/single-customer)
#                  1 = revenue compounds through it (mission-critical, diversified, secular)
# The interaction (not the levels) is what matters -- see solvency.py.
# ---------------------------------------------------------------------------
#                       (funding_need, debt_load, rev_durability)
SOLVENCY = {
    "NVIDIA":                  (0.05, 0.05, 0.85),
    "Microsoft":               (0.00, 0.10, 0.95),
    "Alphabet":                (0.00, 0.05, 0.90),
    "Meta":                    (0.05, 0.10, 0.85),
    "Apple":                   (0.00, 0.15, 0.85),
    "Amazon":                  (0.05, 0.20, 0.80),
    "Broadcom":                (0.10, 0.55, 0.80),
    "Oracle":                  (0.20, 0.65, 0.80),   # debt-funded AI capex
    "Cisco":                   (0.00, 0.20, 0.80),
    "IBM":                     (0.10, 0.45, 0.75),
    "Texas Instruments":       (0.05, 0.20, 0.65),
    "Qualcomm":                (0.05, 0.20, 0.65),
    "ARM":                     (0.05, 0.10, 0.70),
    "Palantir":                (0.05, 0.05, 0.75),   # now FCF-positive
    "AMD":                     (0.10, 0.15, 0.60),
    "Marvell":                 (0.15, 0.25, 0.60),
    "Astera Labs":             (0.10, 0.05, 0.70),
    "AppLovin":                (0.10, 0.25, 0.55),
    "Vertiv":                  (0.15, 0.35, 0.65),
    "Tesla":                   (0.10, 0.20, 0.55),
    "Lumentum":                (0.25, 0.35, 0.50),
    "Coherent":                (0.30, 0.60, 0.55),   # LBO legacy debt
    "Micron":                  (0.25, 0.30, 0.30),   # deeply cyclical revenue
    "Kioxia":                  (0.35, 0.55, 0.30),   # cyclical + levered
    "Samsung":                 (0.05, 0.15, 0.45),   # diversified conglomerate, fortress B/S, cyclical memory rev
    "SK Hynix":                (0.20, 0.40, 0.40),   # memory pure-play, moderate debt, cyclical
    "Applied Optoelectronics": (0.45, 0.30, 0.35),   # lumpy single-customer revenue
    "IonQ":                    (0.90, 0.10, 0.30),   # pre-revenue, equity-funded burn
    "CoreWeave":               (0.85, 0.90, 0.45),   # GPU debt + AI-capex-dependent revenue
}
SOLVENCY_DEFAULT = (0.10, 0.20, 0.70)   # broad ETFs / unknown: low financing risk


def solvency_inputs(name):
    base = name.split(" (")[0].strip()
    for k, v in SOLVENCY.items():
        if k.lower() == base.lower():
            return v
    return SOLVENCY_DEFAULT


# ---------------------------------------------------------------------------
# CAPEX INTENSITY (capex / revenue) -- the AI-buildout operating-leverage risk.
# Heavy capex (>>15% of revenue) means severe operating leverage: if demand
# slows or credit freezes, margins crater and recovery drags. Hardware SELLERS
# (NVDA) are capex-light; hardware BUYERS (Meta/MSFT/CoreWeave) are capex-heavy.
# ESTIMATES. Feeds a recovery_quality penalty in engine.decompose_premium.
# ---------------------------------------------------------------------------
CAPEX_INTENSITY = {
    "Meta": 0.24, "Microsoft": 0.21, "Alphabet": 0.22, "Amazon": 0.15,
    "CoreWeave": 0.85, "IonQ": 0.35, "Tesla": 0.12, "Oracle": 0.18,
    "NVIDIA": 0.03, "Apple": 0.04, "Broadcom": 0.02, "Qualcomm": 0.03, "ARM": 0.01,
    "Micron": 0.35, "Kioxia": 0.30, "Samsung": 0.18, "SK Hynix": 0.25,
    "Palantir": 0.01, "AppLovin": 0.01, "Marvell": 0.06, "AMD": 0.05,
    "Astera Labs": 0.05, "Vertiv": 0.05, "Coherent": 0.12, "Lumentum": 0.12,
    "Texas Instruments": 0.20, "Cisco": 0.03, "IBM": 0.05, "Applied Optoelectronics": 0.15,
}
CAPEX_DEFAULT = 0.08


def capex_intensity(name):
    base = name.split(" (")[0].strip()
    for k, v in CAPEX_INTENSITY.items():
        if k.lower() == base.lower():
            return v
    return CAPEX_DEFAULT
