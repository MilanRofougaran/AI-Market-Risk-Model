"""
provenance.py -- render the input-provenance audit and DRIFT-CHECK it against the live
calibration. Flags HOTSPOTS: inputs that are both high-model-sensitivity (moat, TAM,
revenue-drawdown) AND not high-confidence -- the places optimism overfits. Also confirms
each audited base value still matches the value the engine actually uses, so the audit
cannot silently fall out of date. RESEARCH MODEL -- NOT INVESTMENT ADVICE.

Usage:  python3 provenance.py [NAME ...]      (default: all audited names)
"""
import sys
import calibration as C
from input_provenance import PROVENANCE, FIELD_META

try:
    import extension_data as X
except Exception:
    X = None


def _live_value(name, field):
    """Fetch the value the engine actually uses for (name, field), or None."""
    home = FIELD_META.get(field, {}).get("home")
    try:
        if home == "COMPETITIVE":
            return C.COMPETITIVE.get(name, {}).get(field)
        if home == "OPERATING_LEVERAGE":
            return C.OPERATING_LEVERAGE.get(name, {}).get(field)
        if home == "PRICES":
            return C.PRICES.get(name)
        if home == "PROFIT_SENSITIVITY":
            if field == "cogs_fragility":
                try:
                    import engine as _E
                    return round(_E._effective_cogs_fragility(name), 4)
                except Exception:
                    pass
            return C.PROFIT_SENSITIVITY.get(name, {}).get(field)
        if home == "extension_data" and X is not None:
            if field == "net_cash_to_mcap":
                return getattr(X, "NET_CASH_TO_MCAP", {}).get(name)
        if home == "tam_facts":
            # tam_cagr lives in the discovery TAM facts; surfaced via decompose
            return None
    except Exception:
        return None
    return None


def audit(names=None):
    rows = []
    names = names or list(PROVENANCE.keys())
    for nm in names:
        for field, meta in PROVENANCE.get(nm, {}).items():
            sens = FIELD_META.get(field, {}).get("sensitivity", "?")
            conf = meta["conf"]
            hotspot = (sens.startswith("HIGH")) and (conf != "High")
            live = _live_value(nm, field)
            drift = None
            if live is not None and isinstance(meta.get("base"), (int, float)):
                drift = abs(float(live) - float(meta["base"])) > 1e-6
            rows.append(dict(name=nm, field=field, conf=conf, sens=sens,
                             low=meta.get("low"), base=meta.get("base"), high=meta.get("high"),
                             src=meta.get("src"), note=meta.get("note", ""),
                             hotspot=hotspot, drift=drift))
    return rows


def fmt(rows):
    out = []
    out.append(f"{'Name':12s} {'field':16s} {'conf':>7s} {'sens':>12s} {'low/base/high':>16s} {'flag':>9s}  source")
    out.append("-" * 96)
    for r in rows:
        rng = f"{r['low']}/{r['base']}/{r['high']}"
        flag = ("HOT+DRIFT" if (r["hotspot"] and r["drift"]) else "HOTSPOT" if r["hotspot"] else "DRIFT!" if r["drift"] else "")
        out.append(f"{r['name']:12s} {r['field']:16s} {r['conf']:>7s} {r['sens']:>12s} {rng:>16s} {flag:>9s}  {r['src']}")
    return "\n".join(out)


def summary(rows):
    hot = [r for r in rows if r["hotspot"]]
    drift = [r for r in rows if r["drift"]]
    lines = []
    lines.append(f"\n{len(rows)} audited inputs across {len(set(r['name'] for r in rows))} names.")
    lines.append(f"HOTSPOTS (high-sensitivity AND not high-confidence): {len(hot)}")
    for r in sorted(hot, key=lambda r: (r['field'], r['name'])):
        lines.append(f"   - {r['name']} / {r['field']} ({r['conf']} conf, {r['sens']} sens): {r['note']}")
    if drift:
        lines.append(f"\n!! DRIFT: {len(drift)} audited base values no longer match live calibration:")
        for r in drift:
            lines.append(f"   - {r['name']} / {r['field']}: audit base={r['base']} vs live={_live_value(r['name'], r['field'])}")
    else:
        lines.append("\nDrift check: all audited base values match the live calibration. OK")
    lines.append("\nHotspots are where to spend review effort: a wrong moat or TAM there moves the")
    lines.append("verdict most and is least certain. This layer adds no precision -- it makes the")
    lines.append("judgments explicit. RESEARCH MODEL -- NOT INVESTMENT ADVICE.")
    return "\n".join(lines)


if __name__ == "__main__":
    rows = audit(sys.argv[1:] or None)
    print(fmt(rows))
    print(summary(rows))
