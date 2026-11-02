"""EU robustness (course requirement): replace G-SWA remote-work measures with EWCS
(EWCTS 2021) telework indices on the European country-pair sub-sample.

Design: EWCS 2021 is a cross-section (fielded Mar-Nov 2021), so we estimate
pair-level gravity regressions of post-survey collaboration (2022Q1-2023Q4 mean)
and of collaboration growth (post minus 2021H1) on bilateral telework intensity
interacted with Hofstede cultural distance.
"""
import itertools
import pandas as pd
import numpy as np
import pyfixest as pf

HOF_DIMS = ["pdi", "idv", "mas", "uai", "ltowvs", "ivr"]
WGI_DIMS = ["wgi_va", "wgi_pv", "wgi_ge", "wgi_rq", "wgi_rl", "wgi_cc"]


def build():
    wbc = pd.read_csv("data/raw/wb_countries.csv")
    iso2_to_iso3 = dict(zip(wbc.iso2, wbc.iso3)) | {"XK": "XKX", "TW": "TWN"}
    tw = pd.read_csv("data/processed/ewcs_telework.csv")
    tw["iso3"] = tw.iso3  # already iso3

    countries = sorted(set(tw.iso3))
    ec = pd.read_csv("data/raw/economy_collaborators.csv").dropna(subset=["source", "destination"])
    ec = ec[~ec.source.isin(["EU"]) & ~ec.destination.isin(["EU"])]
    ec["iso3_o"] = ec.source.map(iso2_to_iso3)
    ec["iso3_d"] = ec.destination.map(iso2_to_iso3)
    ec = ec[ec.iso3_o.isin(countries) & ec.iso3_d.isin(countries)
            & (ec.iso3_o != ec.iso3_d) & ec.year.notna()]
    ec["year"] = ec.year.astype(int); ec["quarter"] = ec.quarter.astype(int)
    ec["ln_collab"] = np.log1p(ec.weight)
    post = ec[ec.t.isin([f"{y}Q{q}" for y, q in itertools.product([2022, 2023], [1, 2, 3, 4])])] \
        if "t" in ec else None
    ec["t"] = ec.year.astype(str) + "Q" + ec.quarter.astype(str)
    post = ec[ec.t.str.startswith(("2022", "2023"))].groupby(["iso3_o", "iso3_d"]).ln_collab.mean()
    pre = ec[ec.t.isin(["2021Q1", "2021Q2"])].groupby(["iso3_o", "iso3_d"]).ln_collab.mean()

    # distances + gravity
    hof = pd.read_csv("data/raw/hofstede_clean.csv").set_index("iso3")
    wgi = pd.read_csv("data/raw/wgi_clean.csv").set_index("iso3")
    zs_hof = (hof[HOF_DIMS] - hof[HOF_DIMS].mean()) / hof[HOF_DIMS].std(ddof=0)
    zs_wgi = (wgi[WGI_DIMS] - wgi[WGI_DIMS].mean()) / wgi[WGI_DIMS].std(ddof=0)
    grav = pd.read_csv("data/raw/cepii_bilateral.csv")

    rows = []
    for i, j in itertools.product(countries, countries):
        if i == j:
            continue
        r = {"iso3_o": i, "iso3_d": j}
        if i not in zs_hof.index or j not in zs_hof.index:
            continue
        if not (zs_hof.loc[i].notna().all() and zs_hof.loc[j].notna().all()):
            continue
        r["cult_dist"] = float(((zs_hof.loc[i] - zs_hof.loc[j]) ** 2).mean())
        if i in zs_wgi.index and j in zs_wgi.index:
            r["inst_dist"] = float(((zs_wgi.loc[i] - zs_wgi.loc[j]) ** 2).mean())
        ti = tw.set_index("iso3")
        r["tw_o"] = ti.loc[i, "telework_any_pct"]
        r["tw_d"] = ti.loc[j, "telework_any_pct"]
        r["twr_o"] = ti.loc[i, "telework_regular_pct"]
        r["twr_d"] = ti.loc[j, "telework_regular_pct"]
        r["ln_collab_post"] = post.get((i, j), np.nan)
        r["ln_collab_pre"] = pre.get((i, j), np.nan)
        rows.append(r)
    d = pd.DataFrame(rows).dropna(subset=["ln_collab_post"])
    d = d.merge(grav[["iso3_o", "iso3_d", "dist", "tzdiff", "comlang_off", "contig"]],
                on=["iso3_o", "iso3_d"], how="left")
    d = d.dropna(subset=["dist"])
    d["ln_dist"] = np.log(d.dist)
    d["d_ln_collab"] = d.ln_collab_post - d.ln_collab_pre.fillna(d.ln_collab_pre.mean())
    d["tw_ij"] = (d.tw_o + d.tw_d) / 2
    d["twr_ij"] = (d.twr_o + d.twr_d) / 2
    zc = (d.cult_dist - d.cult_dist.mean()) / d.cult_dist.std(ddof=0)
    zi = (d.inst_dist - d.inst_dist.mean()) / d.inst_dist.std(ddof=0)
    d["tw_x_cult"] = d.tw_ij * zc
    d["tw_x_inst"] = d.tw_ij * zi
    d["twr_x_cult"] = d.twr_ij * zc
    d["pairu"] = d.apply(lambda r: "-".join(sorted([r.iso3_o, r.iso3_d])), axis=1)
    d.to_csv("data/processed/ewcs_pairs.csv", index=False)
    print("EWCS pair sample:", d.shape, "countries:", d.iso3_o.nunique())
    return d


def run(d):
    G = "ln_dist + tzdiff + comlang_off + contig"
    specs = [
        ("Level: any telework x cult", f"ln_collab_post ~ tw_o + tw_d + tw_x_cult + {G}"),
        ("Level: any telework x inst", f"ln_collab_post ~ tw_o + tw_d + tw_x_inst + {G}"),
        ("Level: regular telework x cult", f"ln_collab_post ~ twr_o + twr_d + twr_x_cult + {G}"),
        ("Growth 2021->23: any telework x cult", f"d_ln_collab ~ tw_o + tw_d + tw_x_cult + {G}"),
        ("Growth: regular telework x cult", f"d_ln_collab ~ twr_o + twr_d + twr_x_cult + {G}"),
    ]
    rows = []
    for name, f in specs:
        m = pf.feols(f, data=d, vcov={"CRV1": "pairu"})
        td = m.tidy()
        out = {"spec": name, "N": m._N, "R2": round(float(m._r2), 3)}
        for v in ["tw_o", "tw_d", "twr_o", "twr_d", "tw_x_cult", "tw_x_inst", "twr_x_cult"]:
            if v in td.index:
                r = td.loc[v]
                star = "***" if r["Pr(>|t|)"] < .01 else "**" if r["Pr(>|t|)"] < .05 \
                    else "*" if r["Pr(>|t|)"] < .1 else ""
                out[v] = f"{r.Estimate:.3f}{star} ({r['Std. Error']:.3f})"
        rows.append(out)
    res = pd.DataFrame(rows).fillna("")
    res.to_csv("output/tables/tab_ewcs_eu.csv", index=False)
    print(res.to_string(index=False))
    return res


if __name__ == "__main__":
    d = build()
    run(d)
    # validation: correlation of EWCS telework with G-SWA planned WFH (2022 wave)
    tw = pd.read_csv("data/processed/ewcs_telework.csv").set_index("iso3")
    cw = pd.read_csv("data/processed/gswa_micro_country_wave.csv")
    w2 = cw[cw.wave == 2].set_index("iso3")
    common = tw.index.intersection(w2.index)
    print(f"\nEWCS any-telework% vs G-SWA planned WFH days (2022), n={len(common)}: "
          f"corr={float(np.corrcoef(tw.loc[common,'telework_any_pct'], w2.loc[common,'wfh_employer_plan'])[0,1]):.3f}; "
          f"vs actual days: {float(np.corrcoef(tw.loc[common,'telework_any_pct'], w2.loc[common,'wfh_actual'])[0,1]):.3f}")
