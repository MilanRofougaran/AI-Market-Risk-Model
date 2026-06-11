"""
spread_lens.py -- bull-call-spread analysis from options_lens.json (no re-simulation).
Spread fair = fair(K1) - fair(K2); P(max) = P(S>K2); tail give-up = fair(K2)/fair(K1).
Archetype rule: cyclical -> spreads efficient (bounded rebound, cheap tail to sell);
secular -> graded CAUTION (moderate >35%, large >55% give-up); broken -> still gated.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import json
PAIRS=[("0.75","1.00"),("0.90","1.10"),("0.90","1.20"),("1.00","1.20"),
       ("0.75","1.50"),("0.75","2.00"),("0.75","2.25"),("1.00","2.00")]
FLIES=[("0.90","1.00","1.10"),("0.80","1.00","1.20"),("1.00","1.10","1.20"),   # symmetric
       ("0.90","1.00","1.20"),("0.90","1.10","1.50"),("1.00","1.20","1.75")]   # broken-wing
TAILS=[("0.75","1.50","2.25"),("0.75","1.50","2.00"),("0.75","1.75","2.50"),   # tail-kicker +1/-1/+1
       ("0.90","1.20","2.00"),("1.00","1.50","2.25")]
o=json.load(open("options_lens.json"))
out={"note":__doc__.strip(),"names":{}}
L=["# Bull call spreads — model fair debits (physical measure)","",
   "tail give-up = short-leg fair / long-leg fair — the share of the long call's value you sell.",
   "Rule: cyclicals tolerate spreads (bounded rebound); seculars: moderate CAUTION >35%, large CAUTION >55% give-up. Far-OTM overwrites (K2 >= 1.50) sell only the extreme tail. Tail-kickers (+1/-1/+1) cap a middle band but keep the far tail — the secular-consistent 3-leg. Butterflies (1-2-1) are body bets: legitimate on cyclicals post-trough, CAUTION on seculars (sells the tail twice). Net-naked upper shorts (ratio ladders) are NOT priced — banned structure.",""]
for nm,nd in o["names"].items():
    gate=nd.get("gate",""); out["names"][nm]={"gate":gate,"tenors":{}}
    L+=[f"## {nm} — gate: {gate}","",
        "| Tenor | K1/K2 | width% | fair debit% | P(max) | P(between) | tail give-up |","|---|---|---|---|---|---|---|"]
    for t in ("6m","12m","18m","24m","36m"):
        if t not in nd: continue
        st=nd[t]["strikes"]; out["names"][nm]["tenors"][t]={}
        for k1,k2 in PAIRS:
            if k1 not in st or k2 not in st: continue
            f1,f2=st[k1]["fair_value_pct_of_spot"],st[k2]["fair_value_pct_of_spot"]
            p1,p2=st[k1]["p_itm"],st[k2]["p_itm"]
            width=(float(k2)-float(k1))*100; fair=round(f1-f2,1)
            give=round(f2/f1,2) if f1>0 else None
            out["names"][nm]["tenors"][t][f"{k1}/{k2}"]={"width_pct":width,"fair_debit_pct":fair,
                "p_max":p2,"p_between":round(p1-p2,3),"tail_giveup":give}
            L.append(f"| {t} | {k1}/{k2} | {width:.0f}% | {fair}% | {p2:.0%} | {p1-p2:.0%} | {give:.0%} |")
    L+=["","| Tenor | fly K1/K2/K3 | fair | max (at K2) | P(body) | payoff above wings |","|---|---|---|---|---|---|"]
    for t in ("6m","12m","18m","24m","36m"):
        if t not in nd: continue
        st=nd[t]["strikes"]; out["names"][nm]["tenors"].setdefault(t,{})
        for k1,k2,k3 in FLIES:
            if not all(k in st for k in (k1,k2,k3)): continue
            f1,f2,f3=(st[k]["fair_value_pct_of_spot"] for k in (k1,k2,k3))
            p1,p3=st[k1]["p_itm"],st[k3]["p_itm"]
            fair=round(f1-2*f2+f3,1)
            mx=(float(k2)-float(k1))*100
            above=round(((float(k2)-float(k1))-(float(k3)-float(k2)))*100,0)
            out["names"][nm]["tenors"][t][f"{k1}/{k2}/{k3}"]={"fair_pct":fair,"max_pct":mx,
                "p_body":round(p1-p3,3),"payoff_above_wings_pct":above}
            L.append(f"| {t} | {k1}/{k2}/{k3} | {fair}% | {mx:.0f}% | {p1-p3:.0%} | {above:+.0f}% |")
    L+=["","| Tenor | tail-kicker +K1/-K2/+K3 | fair | capped-zone payoff | P(capped zone) | P(tail kept) | net tail sold |","|---|---|---|---|---|---|---|"]
    for t in ("6m","12m","18m","24m","36m"):
        if t not in nd: continue
        st=nd[t]["strikes"]; out["names"][nm]["tenors"].setdefault(t,{})
        for k1,k2,k3 in TAILS:
            if not all(k in st for k in (k1,k2,k3)): continue
            f1,f2,f3=(st[k]["fair_value_pct_of_spot"] for k in (k1,k2,k3))
            p2,p3=st[k2]["p_itm"],st[k3]["p_itm"]
            fair=round(f1-f2+f3,1); cap=(float(k2)-float(k1))*100
            sold=round((f2-f3)/f1,2) if f1>0 else None
            out["names"][nm]["tenors"][t][f"+{k1}/-{k2}/+{k3}"]={"fair_pct":fair,"capped_zone_pct":cap,
                "p_capped":round(p2-p3,3),"p_tail_kept":p3,"net_tail_sold":sold}
            L.append(f"| {t} | +{k1}/-{k2}/+{k3} | {fair}% | {cap:.0f}% then slope resumes | {p2-p3:.0%} | {p3:.0%} | {sold:.0%} |")
    L.append("")
json.dump(out,open("spread_lens.json","w"),indent=1)
open("spread_lens.md","w").write("\n".join(L))
print("wrote spread_lens.md / spread_lens.json")
