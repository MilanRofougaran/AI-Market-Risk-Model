"""Dip-buying experiment: after a >25% fall, does a call at the dip pay?
v2 (PV-consistent, credit: Gemini review 2026-06-10): payoffs are now DISCOUNTED
at the same 10y rate the options_lens premiums already carry, so exp_net is a
present-value edge. v1 mixed FV payoffs with PV premiums and overstated long
tenors by ~(1-disc)*E[payoff]."""
import numpy as np, zlib, json, sys
import calibration as C, engine as E
RF=(C.MACRO.get("ust_10y") or 4.0)/100.0

PATHS=8000; DIPWIN=126; DAYS=126+756
EXP=[("6m",126),("12m",252),("18m",378),("24m",504),("36m",756)]
NAMES=["Micron","NVIDIA","AMD"]
# ATM fair premiums (% of spot) from options_lens 8k run, per name/tenor:
PREM={"NVIDIA":{"6m":.100,"12m":.159,"18m":.209,"24m":.255,"36m":.338},
      "Micron":{"6m":.090,"12m":.139,"18m":.179,"24m":.216,"36m":.281},
      "AMD":{"6m":.091,"12m":.138,"18m":.178,"24m":.213,"36m":.272}}

decomp=E.decompose_premium()
rng=np.random.default_rng(C.SIM["seed"])
idio={nm:np.random.default_rng((C.SIM["seed"]^(zlib.crc32(nm.encode())&0xFFFFFFFF))&0xFFFFFFFF) for nm in decomp}
res={nm:{l:[] for l,_ in EXP} for nm in NAMES}; ndip={nm:0 for nm in NAMES}; ntot=0
done=0; CH=4000
while done<PATHS:
    n=min(CH,PATHS-done)
    factor,crisis,grind=E._simulate_factor(rng,n,DAYS,return_grind=True)
    subf={g:rng.standard_normal((n,DAYS)) for g in getattr(C,"GROUP_RHO",{})}
    for nm in decomp:
        spec=E.company_to_spec(decomp[nm],name=nm)
        price=E._price_path(rng,factor,crisis,spec,n,DAYS,tail_mult=spec["tail_mult"],
                            subfactors=subf,grind=grind,idio_rng=idio[nm])
        if nm not in NAMES: continue
        peak=np.maximum.accumulate(price[:,:DIPWIN],axis=1)
        dd=price[:,:DIPWIN]/peak-1.0
        hit=dd<=-0.25
        has=hit.any(axis=1); t0=np.argmax(hit,axis=1)
        idx=np.where(has)[0]; ndip[nm]+=len(idx)
        entry=price[idx,t0[idx]]
        for lab,d in EXP:
            ratio=price[idx,t0[idx]+d]/entry
            res[nm][lab].append(ratio)
    ntot+=n; done+=n
    print(f"  {done}/{PATHS}",file=sys.stderr)

out={"paths":PATHS,"dipwin_days":DIPWIN,"names":{}}
for nm in NAMES:
    out["names"][nm]={"p_dip_6m":round(ndip[nm]/PATHS,3),"tenors":{}}
    for lab,d in EXP:
        r=np.concatenate(res[nm][lab]); prem=PREM[nm][lab]
        disc=float(np.exp(-RF*(d/252.0)))
        pay_pv=np.maximum(r-1,0)*disc
        out["names"][nm]["tenors"][lab]={
            "p_itm":round(float(np.mean(r>1.0)),3),
            "p_profit_net":round(float(np.mean(pay_pv-prem>0)),3),
            "exp_net_pv_pct":round(float(np.mean(pay_pv-prem))*100,1),
            "disc":round(disc,4),
            "med":round(float(np.median(r)),3),
            "p10":round(float(np.percentile(r,10)),3),
            "p90":round(float(np.percentile(r,90)),3)}
json.dump(out,open("dip_experiment.json","w"),indent=1)
for nm in NAMES:
    o=out["names"][nm]
    print(f"\n{nm}  (P(>25% dip within 6m)={o['p_dip_6m']:.0%}, n={ndip[nm]})")
    print(f"  {'tenor':5s} {'P(ITM)':>7s} {'P(profit,net)':>13s} {'E[net,PV]':>9s} {'med S/entry':>11s}")
    for lab,_ in EXP:
        t=o["tenors"][lab]
        print(f"  {lab:5s} {t['p_itm']:>6.0%} {t['p_profit_net']:>12.0%} {t['exp_net_pv_pct']:>8.1f}% {t['med']:>10.2f}")
