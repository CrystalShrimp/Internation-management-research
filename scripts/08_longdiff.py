"""Long-difference design: change in bilateral collaboration on change in remote work.

Quarterly sample (G-SWA): 2021Q3-2022Q4 (W1/W2 regime) vs 2023Q2-Q4 (W3 regime).
EU sample (Eurostat): 2019 vs 2023 (durable shift) and 2019 vs 2021 (pandemic shock).
Cross-section of directed pairs -> direct test of H1 (promotion) and H2 (distance moderation).
"""
import os
import pandas as pd
import numpy as np
import pyfixest as pf


def longdiff_gswa():
    p = pd.read_csv("data/processed/panel_pair_quarter.csv")
    pre = p[p.t.isin(["2021Q3", "2021Q4", "2022Q1", "2022Q2", "2022Q3", "2022Q4"])]
    post = p[p.t.isin(["2023Q2", "2023Q3", "2023Q4"])]
    d = pd.DataFrame({
        "d_ln_collab": post.groupby("pair").ln_collab.mean() - pre.groupby("pair").ln_collab.mean(),
        "d_collab": post.groupby("pair").collaborators.mean() - pre.groupby("pair").collaborators.mean(),
        "d_ln_dev_o": post.groupby("pair").ln_dev_o.mean() - pre.groupby("pair").ln_dev_o.mean(),
        "d_ln_dev_d": post.groupby("pair").ln_dev_d.mean() - pre.groupby("pair").ln_dev_d.mean(),
    }).reset_index()
    base = p.drop_duplicates("pair")[
        ["pair", "iso3_o", "iso3_d", "dist_z", "cult_dist", "inst_dist", "ln_dist", "tzdiff",
         "comlang_off", "contig", "scaled_sci_2021"]]
    d = d.merge(base, on="pair")

    w12 = pd.read_csv("data/raw/gswa_w1w2.csv").set_index("iso3")
    w3 = pd.read_csv("data/raw/gswa_w3.csv").set_index("iso3")
    for s in ["o", "d"]:
        c = d[f"iso3_{s}"]
        d[f"d_plan_{s}"] = c.map(w3.wfh_employer_plan) - c.map(w12.wfh_employer_plan)
        d[f"d_actual_{s}"] = c.map(w3.wfh_actual) - c.map(w12.wfh_actual)
        d[f"d_desire_{s}"] = c.map(w3.wfh_worker_desire) - c.map(w12.wfh_worker_desire)
    d["d_plan_ij"] = (d.d_plan_o + d.d_plan_d) / 2
    d["d_actual_ij"] = (d.d_actual_o + d.d_actual_d) / 2
    d["d_desire_ij"] = (d.d_desire_o + d.d_desire_d) / 2
    for dist in ["dist_z", "cult_dist", "inst_dist"]:
        z = (d[dist] - d[dist].mean()) / d[dist].std(ddof=0)
        d[f"plan_x_{dist}"] = d.d_plan_ij * z
        d[f"actual_x_{dist}"] = d.d_actual_ij * z
    d.to_csv("data/processed/longdiff_gswa.csv", index=False)

    specs = [
        "d_ln_collab ~ d_plan_o + d_plan_d",
        "d_ln_collab ~ d_plan_o + d_plan_d + plan_x_dist_z",
        "d_ln_collab ~ d_plan_o + d_plan_d + plan_x_dist_z + ln_dist + tzdiff + comlang_off",
        "d_ln_collab ~ d_plan_o + d_plan_d + plan_x_cult_dist + ln_dist + tzdiff + comlang_off",
        "d_ln_collab ~ d_plan_o + d_plan_d + plan_x_inst_dist + ln_dist + tzdiff + comlang_off",
        "d_ln_collab ~ d_plan_o + d_plan_d + plan_x_dist_z + d_ln_dev_o + d_ln_dev_d",
    ]
    fits = [pf.feols(f, data=d, vcov={"HC1": "pair"}) if False else pf.feols(
        f, data=d) for f in specs]
    # cluster by the unordered pair
    d["pairu"] = d.apply(lambda r: "-".join(sorted([r.iso3_o, r.iso3_d])), axis=1)
    fits = [pf.feols(f, data=d, vcov={"CRV1": "pairu"}) for f in specs]
    os.makedirs("output/tables", exist_ok=True)
    tab = pf.etable(fits, type="df")
    tab.to_csv("output/tables/tab4_longdiff_gswa.csv")
    print("GSWA long-diff (N pairs =", len(d), "):")
    print(tab.to_string())
    return d


def longdiff_eu():
    p = pd.read_csv("data/processed/panel_eu_year.csv")

    def diff(y0, y1, tag):
        a = p[p.year == y0].set_index("pair")
        b = p[p.year == y1].set_index("pair")
        common = a.index.intersection(b.index)
        d = pd.DataFrame({
            "d_ln_collab": b.loc[common, "ln_collab"] - a.loc[common, "ln_collab"],
            "d_remote_o": b.loc[common, "remote_o"] - a.loc[common, "remote_o"],
            "d_remote_d": b.loc[common, "remote_d"] - a.loc[common, "remote_d"],
            "d_ln_dev_o": b.loc[common, "ln_dev_o"] - a.loc[common, "ln_dev_o"],
            "d_ln_dev_d": b.loc[common, "ln_dev_d"] - a.loc[common, "ln_dev_d"],
            "remote_o_l": b.loc[common, "remote_o"], "remote_d_l": b.loc[common, "remote_d"],
        }).reset_index().merge(
            p.drop_duplicates("pair")[["pair", "iso3_o", "iso3_d", "dist_z", "cult_dist",
                                       "inst_dist", "dist", "tzdiff", "comlang_off", "contig"]],
            on="pair")
        d["d_remote_ij"] = (d.d_remote_o + d.d_remote_d) / 2
        for dist in ["dist_z", "cult_dist", "inst_dist"]:
            z = (d[dist] - d[dist].mean()) / d[dist].std(ddof=0)
            d[f"remote_x_{dist}"] = d.d_remote_ij * z
        d["ln_dist"] = np.log(d["dist"])
        d["pairu"] = d.apply(lambda r: "-".join(sorted([r.iso3_o, r.iso3_d])), axis=1)
        # GitHub developer series starts 2020Q1: recompute developer growth vs 2020
        a20 = p[p.year == 2020].set_index("pair")
        d["d_ln_dev_o"] = [b.loc[x, "ln_dev_o"] - a20.loc[x, "ln_dev_o"]
                           if x in a20.index else np.nan for x in d.pair]
        d["d_ln_dev_d"] = [b.loc[x, "ln_dev_d"] - a20.loc[x, "ln_dev_d"]
                           if x in a20.index else np.nan for x in d.pair]
        d.to_csv(f"data/processed/longdiff_eu_{tag}.csv", index=False)
        return d

    d = diff(2019, 2023, "23")
    print(f"EU long-diff 2019->2023 (N={len(d)}):")
    specs = [
        "d_ln_collab ~ d_remote_o + d_remote_d",
        "d_ln_collab ~ d_remote_o + d_remote_d + remote_x_dist_z",
        "d_ln_collab ~ d_remote_o + d_remote_d + remote_x_dist_z + ln_dist + tzdiff + comlang_off",
        "d_ln_collab ~ d_remote_o + d_remote_d + remote_x_cult_dist + ln_dist + tzdiff + comlang_off",
        "d_ln_collab ~ d_remote_o + d_remote_d + remote_x_inst_dist + ln_dist + tzdiff + comlang_off",
        "d_ln_collab ~ d_remote_o + d_remote_d + remote_x_dist_z + d_ln_dev_o + d_ln_dev_d",
    ]
    fits = [pf.feols(f, data=d, vcov={"CRV1": "pairu"}) for f in specs]
    tab = pf.etable(fits, type="df")
    tab.to_csv("output/tables/tab5_longdiff_eu.csv")
    print(tab.to_string())

    d21 = diff(2019, 2021, "21")
    print(f"EU long-diff 2019->2021 pandemic shock (N={len(d21)}):")
    fits21 = [
        pf.feols("d_ln_collab ~ d_remote_o + d_remote_d + remote_x_dist_z + ln_dist + tzdiff + comlang_off",
                 data=d21, vcov={"CRV1": "pairu"}),
        pf.feols("d_ln_collab ~ d_remote_o + d_remote_d + remote_x_cult_dist + ln_dist + tzdiff + comlang_off",
                 data=d21, vcov={"CRV1": "pairu"}),
    ]
    pf.etable(fits21, type="df").to_csv("output/tables/tab6_longdiff_eu_2021.csv")
    print(pf.etable(fits21, type="df").to_string())
    return d


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "eu":
        longdiff_eu()
    elif len(sys.argv) > 1 and sys.argv[1] == "gswa":
        longdiff_gswa()
    else:
        import subprocess
        subprocess.run([sys.executable, "-X", "utf8", __file__, "gswa"], check=True)
        subprocess.run([sys.executable, "-X", "utf8", __file__, "eu"], check=True)
