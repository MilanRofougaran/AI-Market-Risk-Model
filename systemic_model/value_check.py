"""
value_check.py -- the full two-ledger view in one command, now with robustness, confidence,
and implied-expectations.
  python3 value_check.py "NVIDIA"                  # stock ledger + tier + confidence + reverse-DCF
  python3 value_check.py "NVIDIA" 30m 0.75 45      # + option verdict (gates, edge, P(profit))
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys, subprocess
import stock_premium as SP
import tier_gate as TG
import confidence as CF
import reverse_dcf as RD

def run():
    if len(sys.argv) < 2:
        print(__doc__); return
    name = sys.argv[1]
    print("=" * 72); print("STOCK")
    R = SP.rows([name])
    print(SP.fmt(name, R[name]) if name in R else f"  {name} not in universe")
    # tier (mandatory haircut panel) + confidence
    t = TG.run([name]).get(name); c = CF.run([name]).get(name)
    if t:
        f = t["fragility"]
        print(f"  TIER {t['tier']}  | fragility panel  base {f['base']:.2f} / TAM {f['TAM']:.2f} / "
              f"moat-.15 {f['moat-.15']:.2f} / margin {f['margin']:.2f}  (worst {t['worst']:.2f})")
    if c:
        print(f"  CONFIDENCE  inputs {c['input_conf']:.2f}  | P(never) {c['pnever_conf']}  "
              f"| option-fair {c['option_conf']}  | anchored$ {c['anchor_conf']}")
    rd = RD.implied(name)
    if rd: print("  " + RD.fmt(rd).replace("\n", "\n  "))
    if len(sys.argv) >= 5:
        print("=" * 72); print("OPTION")
        out = subprocess.run([sys.executable, "premium_check.py", *sys.argv[1:]],
                             capture_output=True, text=True)
        print(out.stdout.rstrip() or out.stderr.rstrip())

if __name__ == "__main__":
    run()
