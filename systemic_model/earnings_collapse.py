"""
earnings_collapse.py -- the cyclical EARNINGS-COLLAPSE (denominator) diagnostic.
In a bust, operating leverage makes EPS fall faster than price -> the trailing P/E EXPANDS
exactly when you need it to compress, and recovery must wait for the earnings denominator to
heal before the multiple re-rates. Shows, per name: earnings_cyclicality, the illustrative EPS
trough and resulting P/E expansion, and the recovery-quality drag. High-cyclicality memory names
(Micron/Kioxia) cannot be valued on trough earnings. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys
import calibration as C
import engine as E

def run(names=None):
    d = E.decompose_premium()
    order = names or [n for n in d if "earnings_cyclicality" in d[n]]
    rows = {}
    for nm in order:
        o = d.get(nm, {})
        if "earnings_cyclicality" not in o: continue
        rows[nm] = dict(cyclicality=o["earnings_cyclicality"],
                        recov_pre=o.get("recovery_quality_precollapse"),
                        recov_post=o["recovery_quality"],
                        eps_trough=o.get("eps_trough_depth"),
                        pe_expansion=o.get("pe_expansion_at_trough"))
    return rows

if __name__ == "__main__":
    rows = run(sys.argv[1:] or None)
    print(f"{'Name':12s} {'cyclic':>6s} {'EPS trough':>10s} {'P/E x':>6s} {'recov_q pre->post':>18s}")
    for nm, r in sorted(rows.items(), key=lambda kv: -kv[1]["cyclicality"]):
        print(f"{nm:12s} {r['cyclicality']:>6.2f} {r['eps_trough']:>9.0%} {('~'+str(r['pe_expansion'])+'x'):>6s} "
              f"{r['recov_pre']:>8.2f}->{r['recov_post']:<8.2f}")
    print("\nDepth (trough) and recovery-timing reflect this in the MC; the 7-yr P(never) tail is")
    print("robust (these names recover given time) -- the pain is the WAIT, not permanent loss.")
