"""Robustness checks: marginal effects, alternative measures/DVs, placebo, leave-one-out."""
import os
import subprocess
import sys
import pandas as pd
import numpy as np
import pyfixest as pf

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

BASE = "d_ln_collab ~ d_plan_ij + plan_x_dist_z + ln_dist + tzdiff + comlang_off"


def marginal_effects(d):
    m = pf.feols(BASE, data=d, vcov={"CRV1": "pairu"})
    t = m.tidy()
    b_plan, b_x = t.loc["d_plan_ij", "Estimate"], t.loc["plan_x_dist_z", "Estimate"]
    se_plan, se_x = t.loc["d_plan_ij", "Std. Error"], t.loc["plan_x_dist_z", "Std. Error"]
    zs = np.linspace(-1.5, 2.5, 41)
    me = b_plan + b_x * zs
    # delta-method SE ignoring cov (conservative): combine
    names = list(m.coef().index)
    V = pd.DataFrame(np.asarray(m._vcov), index=names, columns=names)
    cv = V.loc["d_plan_ij", "plan_x_dist_z"]
    se = np.sqrt(se_plan**2 + (zs * se_x)**2 + 2 * zs * cv)
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    ax.plot(zs, me, color="#4C72B0", lw=1.5)
    ax.fill_between(zs, me - 1.96 * se, me + 1.96 * se, alpha=.2, color="#4C72B0")
    ax.axhline(0, color="gray", lw=.8)
    ax.set_xlabel("Bilateral distance (composite z-score)")
    ax.set_ylabel("Effect of +1 planned WFH day on $\\Delta$ln(collaboration)")
    ax.set_title("Marginal effect of remote-work adoption by institutional-cultural distance")
    plt.tight_layout()
    plt.savefig("output/figures/fig5_marginal_effects.png", bbox_inches="tight")
    plt.close()
    print(f"marginal effect at z=-1: {b_plan - b_x:+.3f}, at z=+1: {b_plan + b_x:+.3f}")
    return m


def robustness_table(d):
    p = pd.read_csv("data/processed/panel_pair_quarter.csv")

    specs = {}
    # 1. main (repeat for reference)
    specs["(1) Main: planned WFH"] = BASE
    # 2. worker-desired WFH days
    d2 = d.copy()
    d2["d_desire_ij"] = d2.d_desire_ij
    zz = (d2.dist_z - d2.dist_z.mean()) / d2.dist_z.std(ddof=0)
    d2["desire_x_dist"] = d2.d_desire_ij * zz
    specs["(2) Desired WFH days"] = ("d_ln_collab ~ d_desire_ij + desire_x_dist + ln_dist + "
                                     "tzdiff + comlang_off")
    # 3. actual WFH days (lockdown-contaminated; expect artifact)
    d2["actual_x_dist"] = d2.d_actual_ij * zz
    specs["(3) Actual WFH days"] = ("d_ln_collab ~ d_actual_ij + actual_x_dist + ln_dist + "
                                    "tzdiff + comlang_off")
    # 4. winsorised outcome (5%)
    lo, hi = d.d_ln_collab.quantile([.05, .95])
    d2["d_ln_w"] = d.d_ln_collab.clip(lo, hi)
    specs["(4) Winsorised dv"] = "d_ln_w ~ d_plan_ij + plan_x_dist_z + ln_dist + tzdiff + comlang_off"
    # 5. drop US pairs
    d_nous = d2[~d2.iso3_o.eq("USA") & ~d2.iso3_d.eq("USA")]
    # 6. drop China pairs
    d_nochn = d2[~d2.iso3_o.eq("CHN") & ~d2.iso3_d.eq("CHN")]

    rows = []
    for label, f in specs.items():
        m = pf.feols(f, data=d2, vcov={"CRV1": "pairu"})
        td = m.tidy().reset_index()
        rows.append(_row(label, td, m))
    for label, dd in [("(5) Drop US pairs", d_nous), ("(6) Drop China pairs", d_nochn)]:
        m = pf.feols(BASE, data=dd, vcov={"CRV1": "pairu"})
        td = m.tidy().reset_index()
        rows.append(_row(label, td, m))

    # 7. placebo: fake break at 2022Q3 within pre-period
    pre_pre = p[p.t.isin(["2021Q3", "2021Q4", "2022Q1", "2022Q2"])]
    pre_post = p[p.t.isin(["2022Q3", "2022Q4"])]
    dp = pd.DataFrame({
        "d_ln_collab": pre_post.groupby("pair").ln_collab.mean() - pre_pre.groupby("pair").ln_collab.mean(),
    }).reset_index()
    dp = dp.merge(d[["pair", "dist_z", "ln_dist", "tzdiff", "comlang_off", "iso3_o", "iso3_d",
                     "pairu"]], on="pair")
    dp["fake_plan_ij"] = dp.pair.map(
        d.set_index("pair").d_plan_ij)  # uses future change: should NOT predict past
    zz = (dp.dist_z - dp.dist_z.mean()) / dp.dist_z.std(ddof=0)
    dp["fake_x_dist"] = dp.fake_plan_ij * zz
    m = pf.feols("d_ln_collab ~ fake_plan_ij + fake_x_dist + ln_dist + tzdiff + comlang_off",
                 data=dp, vcov={"CRV1": "pairu"})
    td = m.tidy().reset_index()
    rows.append(_row("(7) Placebo: pre-trend 2022H2 vs 2022H1", td, m, x="fake_plan_ij"))

    # 8. lagged wave: W1W2 plan LEVELS -> post-2023 collaboration growth (timing placebo)
    w12 = pd.read_csv("data/raw/archive/wfh_w1w2_nber_table.csv").set_index("iso3")
    d3 = d.copy()
    for s in ["o", "d"]:
        d3[f"plan12_{s}"] = d3[f"iso3_{s}"].map(w12.wfh_employer_plan)
    d3["plan12_ij"] = (d3.plan12_o + d3.plan12_d) / 2
    zz = (d3.dist_z - d3.dist_z.mean()) / d3.dist_z.std(ddof=0)
    d3["plan12_x"] = d3.plan12_ij * zz
    m = pf.feols("d_ln_collab ~ plan12_ij + plan12_x + ln_dist + tzdiff + comlang_off",
                 data=d3, vcov={"CRV1": "pairu"})
    td = m.tidy().reset_index()
    rows.append(_row("(8) Level of planned WFH (W1/W2)", td, m, x="plan12_ij"))

    out = pd.DataFrame(rows)
    os.makedirs("output/tables", exist_ok=True)
    out.to_csv("output/tables/tab7_robustness.csv", index=False)
    print(out.to_string(index=False))
    return out


def _row(label, td, m, x="d_plan_ij"):
    def get(var):
        r = td[td.Coefficient == var]
        if not len(r):
            return ""
        est, se, pv = r["Estimate"].iloc[0], r["Std. Error"].iloc[0], r["Pr(>|t|)"].iloc[0]
        star = "***" if pv < .01 else "**" if pv < .05 else "*" if pv < .1 else ""
        return f"{est:.3f}{star} ({se:.3f})"
    xvar = x if x in set(td.Coefficient) else "d_plan_ij"
    xv = get(xvar)
    xv2 = xv.replace("d_plan_ij", "") if False else xv
    return {"Specification": label, xvar: get(xvar),
            "Interaction (remote x dist)": get(
                {"d_desire_ij": "desire_x_dist", "d_actual_ij": "actual_x_dist",
                 "plan12_ij": "plan12_x", "fake_plan_ij": "fake_x_dist"}.get(xvar, "plan_x_dist_z")),
            "N": int(m._N), "R2": round(float(m._r2), 3)}


if __name__ == "__main__":
    d = pd.read_csv("data/processed/longdiff_gswa.csv")
    d["pairu"] = d.apply(lambda r: "-".join(sorted([r.iso3_o, r.iso3_d])), axis=1)
    d.to_csv("data/processed/longdiff_gswa.csv", index=False)
    marginal_effects(d)
    robustness_table(d)
