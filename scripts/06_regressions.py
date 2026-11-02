"""Baseline gravity regressions: TWFE-OLS and PPML.

ln(1+Collab_ijt) = b1 Remote_it + b2 Remote_jt + b3 (Remote_ijt x Distance_ij)
                   + g X_ijt + mu_ij + lambda_t + e_ijt

Main remote-work measure: employer-planned post-pandemic WFH full days per week
(G-SWA; structural adoption). Actual survey-week WFH days are used as an
alternative in the robustness scripts (pandemic-lockdown contamination).
Clustered SEs at the country-pair level.
"""
import os
import pandas as pd
import numpy as np
import pyfixest as pf

CONTROLS = ["ln_dev_o", "ln_dev_d", "ln_gdp_o", "ln_gdp_d", "broadband_o", "broadband_d"]


def add_plan_vars(df):
    df["remote_plan_ij"] = (df.remote_plan_o + df.remote_plan_d) / 2
    for d in ["cult_dist", "inst_dist", "dist_z"]:
        dz = (df[d] - df[d].mean()) / df[d].std(ddof=0)
        df[f"plan_x_{d}"] = df.remote_plan_ij * dz
    return df


def balanced_with_zeros(p):
    pairs = p[["pair", "iso3_o", "iso3_d", "cult_dist", "inst_dist", "dist_z", "ln_dist",
               "tzdiff", "comlang_off", "contig", "scaled_sci_2021"]].drop_duplicates("pair")
    ts = sorted(p.t.unique())
    idx = pd.MultiIndex.from_product([pairs.pair, ts], names=["pair", "t"]).to_frame(index=False)
    b = idx.merge(pairs, on="pair", how="left").merge(
        p.drop(columns=["iso3_o", "iso3_d", "cult_dist", "inst_dist", "dist_z", "ln_dist",
                        "tzdiff", "comlang_off", "contig", "scaled_sci_2021"]),
        on=["pair", "t"], how="left")
    b["collaborators"] = b.collaborators.fillna(0)
    b["ln_collab"] = np.log1p(b.collaborators)
    b = b.sort_values(["pair", "t"])
    carry = CONTROLS + ["remote_o", "remote_d", "remote_ij", "remote_plan_o", "remote_plan_d",
                        "remote_desire_o", "remote_desire_d",
                        "remote_x_cult_dist", "remote_x_inst_dist", "remote_x_dist_z",
                        "year", "quarter"]
    for c in carry:
        b[c] = b.groupby("pair")[c].transform(lambda s: s.ffill().bfill())
    b = add_plan_vars(b)
    b["ln_int_o"] = b.ln_collab - np.log(b.developers_o)
    b["ln_int_d"] = b.ln_collab - np.log(b.developers_d)
    return b


def run_ols(b):
    # Course spec: country-pair panel with Remote x Distance interaction;
    # Hofstede cultural distance is the designated moderator (WGI institutional as extension)
    specs = [
        "ln_collab ~ remote_plan_o + remote_plan_d",
        "ln_collab ~ remote_plan_o + remote_plan_d + plan_x_cult_dist",
        "ln_collab ~ remote_plan_o + remote_plan_d + plan_x_cult_dist + " + " + ".join(CONTROLS),
        "ln_int_o ~ remote_plan_o + remote_plan_d + plan_x_cult_dist + " + " + ".join(CONTROLS),
        "ln_collab ~ remote_plan_o + remote_plan_d + plan_x_inst_dist + " + " + ".join(CONTROLS),
    ]
    fits = [pf.feols(f + " | pair + t", data=b, vcov={"CRV1": "pair"}) for f in specs]
    tab = pf.etable(fits, type="df")
    os.makedirs("output/tables", exist_ok=True)
    tab.to_csv("output/tables/tab2_baseline_ols.csv")
    print(tab.to_string())
    return fits


def run_ppml(b):
    specs = [
        "collaborators ~ remote_plan_o + remote_plan_d",
        "collaborators ~ remote_plan_o + remote_plan_d + plan_x_cult_dist",
        "collaborators ~ remote_plan_o + remote_plan_d + plan_x_cult_dist + " + " + ".join(CONTROLS),
        "collaborators ~ remote_plan_o + remote_plan_d + plan_x_inst_dist + " + " + ".join(CONTROLS),
    ]
    fits = [pf.fepois(f + " | pair + t", data=b, vcov={"CRV1": "pair"}) for f in specs]
    tab = pf.etable(fits, type="df")
    tab.to_csv("output/tables/tab3_ppml.csv")
    print(tab.to_string())
    return fits


def event_study(b):
    b = b.copy()
    b["dplan"] = b.groupby("pair")["remote_plan_ij"].transform(lambda s: s.iloc[-1] - s.iloc[0])
    qs = sorted(b.t.unique())
    for t in qs[1:]:
        b[f"ev_{t}"] = b.dplan * (b.t == t).astype(float)
    evs = " + ".join(f"ev_{t}" for t in qs[1:])
    m = pf.feols(f"ln_collab ~ {evs} | pair + t", data=b,
                 vcov={"CRV1": "pair"})
    td = m.tidy().reset_index()
    td = td[td.Coefficient.str.startswith("ev_")]
    td["t"] = td.Coefficient.str.replace("ev_", "")
    td["lo"] = td["Estimate"] - 1.96 * td["Std. Error"]
    td["hi"] = td["Estimate"] + 1.96 * td["Std. Error"]
    td.to_csv("output/tables/tab_event_study.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 150, "font.size": 9})
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.errorbar(range(len(td)), td["Estimate"],
                yerr=[td["Estimate"] - td.lo, td.hi - td["Estimate"]],
                marker="o", ms=4, capsize=2.5, lw=1, color="#4C72B0", ecolor="lightgray")
    ax.axhline(0, color="gray", lw=.8)
    ax.axvline(6.5, color="crimson", ls="--", lw=1, label="G-SWA Wave 3 (2023Q2)")
    ax.set_xticks(range(len(td))); ax.set_xticklabels(td.t, rotation=90, fontsize=7)
    ax.set_ylabel("coef. on $\\Delta$Planned remote work $\\times$ quarter")
    ax.set_title("Event study: collaboration response to planned remote-work adoption")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig("output/figures/fig4_event_study.png", bbox_inches="tight")
    plt.close()
    print("saved fig4_event_study.png")
    return m


if __name__ == "__main__":
    p = pd.read_csv("data/processed/panel_pair_quarter.csv")
    b = balanced_with_zeros(p)
    b.to_csv("data/processed/panel_balanced.csv", index=False)
    print("balanced panel:", b.shape)
    run_ols(b)
    run_ppml(b)
    event_study(b)
