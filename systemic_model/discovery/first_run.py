"""First live discovery run, June 2026 broad market screen. (Fixed: pass the
metrics dict to the screen rule, not the wrapper.)"""
import agent, screen_rules as SR, registry as R

etfs = [
 dict(name="SMH (VanEck Semis)", kind="etf", sector="AI/semis",
      demonstrated_growth=0.55, tam_cagr=0.35, penetration=0.30, tam_quality=0.90, conviction=0.90),
 dict(name="SOXX (iShares Semis)", kind="etf", sector="AI/semis",
      demonstrated_growth=0.52, tam_cagr=0.35, penetration=0.30, tam_quality=0.90, conviction=0.88),
 dict(name="FTXL (FT Nasdaq Semis)", kind="etf", sector="AI/semis",
      demonstrated_growth=0.60, tam_cagr=0.35, penetration=0.28, tam_quality=0.85, conviction=0.82),
 dict(name="BAI (BlackRock AI)", kind="etf", sector="AI broad",
      demonstrated_growth=0.40, tam_cagr=0.40, penetration=0.20, tam_quality=0.75, conviction=0.80),
 dict(name="PAVE (US Infrastructure)", kind="etf", sector="infrastructure/power",
      demonstrated_growth=0.18, tam_cagr=0.20, penetration=0.25, tam_quality=0.80, conviction=0.75),
 dict(name="QTUM (Quantum/Compute)", kind="etf", sector="quantum",
      demonstrated_growth=0.20, tam_cagr=0.45, penetration=0.05, tam_quality=0.45, conviction=0.40),
 dict(name="Nuclear/Uranium ETF (URA/NLR)", kind="etf", sector="power/nuclear",
      demonstrated_growth=0.30, tam_cagr=0.25, penetration=0.20, tam_quality=0.75, conviction=0.70),
]
stocks = [
 dict(name="NVIDIA", kind="stock", sector="AI/semis",
      demonstrated_growth=0.66, tam_cagr=0.45, penetration=0.39, tam_quality=0.90, conviction=0.92),
 dict(name="Broadcom", kind="stock", sector="AI/semis",
      demonstrated_growth=0.65, tam_cagr=0.40, penetration=0.27, tam_quality=0.85, conviction=0.88),
 dict(name="AMD", kind="stock", sector="AI/semis",
      demonstrated_growth=0.32, tam_cagr=0.50, penetration=0.03, tam_quality=0.75, conviction=0.78),
 dict(name="Marvell", kind="stock", sector="AI/semis",
      demonstrated_growth=0.42, tam_cagr=0.35, penetration=0.07, tam_quality=0.70, conviction=0.72),
 dict(name="Micron", kind="stock", sector="AI/semis-memory",
      demonstrated_growth=0.57, tam_cagr=0.40, penetration=0.23, tam_quality=0.65, conviction=0.70),
 dict(name="Coherent", kind="stock", sector="AI/optical",
      demonstrated_growth=0.41, tam_cagr=0.40, penetration=0.10, tam_quality=0.80, conviction=0.80),
 dict(name="Lumentum", kind="stock", sector="AI/optical",
      demonstrated_growth=0.65, tam_cagr=0.40, penetration=0.08, tam_quality=0.78, conviction=0.75),
 dict(name="Vistra", kind="stock", sector="power/nuclear",
      demonstrated_growth=0.43, tam_cagr=0.20, penetration=0.15, tam_quality=0.80, conviction=0.78),
 dict(name="Constellation Energy", kind="stock", sector="power/nuclear",
      demonstrated_growth=0.11, tam_cagr=0.20, penetration=0.18, tam_quality=0.82, conviction=0.78),
 dict(name="Applied Optoelectronics", kind="stock", sector="AI/optical",
      demonstrated_growth=0.51, tam_cagr=0.40, penetration=0.04, tam_quality=0.55, conviction=0.45),
 dict(name="IonQ", kind="stock", sector="quantum",
      demonstrated_growth=0.90, tam_cagr=0.45, penetration=0.02, tam_quality=0.40, conviction=0.40),
]

# record into registry (store the screen inputs as the metrics)
run_id = agent.open_run(notes="first live discovery run, June 2026 broad screen")
reg = R.load_registry()
for c in etfs + stocks:
    m = {k: c[k] for k in ("demonstrated_growth","tam_cagr","penetration","tam_quality","conviction")}
    m["kind"] = c["kind"]
    R.record_candidate(reg, run_id, c["name"], c["sector"], m)
R.commit_run(reg, run_id); R.save_registry(reg)
print(f"Opened {run_id}, recorded {len(etfs+stocks)} candidates.\n")

all_etfs = SR.rank(etfs+stocks, kind="etf")
all_stocks = SR.rank(etfs+stocks, kind="stock")
print("="*72); print("RANKED ETF CANDIDATES  (top 3-5 carried forward)"); print("="*72)
for i,c in enumerate(all_etfs,1):
    star = " *" if i<=5 else "  "
    print(f"{star}{i}. {SR.explain(c)}   [{c['sector']}]")
print("\n"+"="*72); print("RANKED STOCK CANDIDATES  (top 6-8 carried forward)"); print("="*72)
for i,c in enumerate(all_stocks,1):
    star = " *" if i<=8 else "  "
    print(f"{star}{i}. {SR.explain(c)}   [{c['sector']}]")
