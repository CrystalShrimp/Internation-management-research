"""v2 regressions on microdata-based panels.

Panel A: 3-wave balanced (11 countries, 2021Q3-2023Q4, two breaks)
Panel B: 2-wave extended (21 countries, 2022Q1-2023Q4, one break)
Main moderator: Hofstede cultural distance (Kogut-Singh, full-sample reference).
"""
import subprocess
import sys
import pandas as pd
import numpy as np
import pyfixest as pf

CONTROLS = ["ln_dev_o", "ln_dev_d", "ln_gdp_o", "ln_gdp_d", "broadband_o", "broadband_d"]


def run_panel(path, tag, drop_gdp=False):
    p = pd.read_csv(path)
    ctrl = [c for c in CONTROLS if not (drop_gdp and "gdp" in c)]
    specs = [
        f"ln_collab ~ remote_plan_o + remote_plan_d + plan_x_cult",
        f"ln_collab ~ remote_plan_o + remote_plan_d + plan_x_cult + " + " + ".join(ctrl),
        f"ln_int_o ~ remote_plan_o + remote_plan_d + plan_x_cult + " + " + ".join(ctrl),
        f"ln_collab ~ remote_plan_o + remote_plan_d + plan_x_inst + " + " + ".join(ctrl),
        f"ln_collab ~ remote_o + remote_d + remote_x_cult + " + " + ".join(ctrl),
        f"collaborators ~ remote_plan_o + remote_plan_d + plan_x_cult + " + " + ".join(ctrl),
    ]
    print(f"\n{'='*70}\n{tag} (N={len(p)}, pairs={p.pair.nunique()}, quarters={p.t.nunique()})")
    fits = []
    for f in specs:
        est = pf.fepois if f.startswith("collaborators") else pf.feols
        m = est(f + " | pair + t", data=p, vcov={"CRV1": "pair"})
        fits.append(m)
    tab = pf.etable(fits, type="df")
    tab.to_csv(f"output/tables/tab_v2_{tag}.csv")
    print(tab.to_string())
    return p, fits


def event_study_a():
    p = pd.read_csv("data/processed/panel_A_3wave.csv")
    p["dplan"] = p.groupby("pair")["remote_plan_ij"].transform(lambda s: s.iloc[-1] - s.iloc[0])
    qs = sorted(p.t.unique())
    for t in qs[1:]:
        p[f"ev_{t}"] = p.dplan * (p.t == t).astype(float)
    evs = " + ".join(f"ev_{t}" for t in qs[1:])
    m = pf.feols(f"ln_collab ~ {evs} | pair + t", data=p, vcov={"CRV1": "pair"})
    td = m.tidy().reset_index()
    td = td[td.Coefficient.str.startswith("ev_")]
    td["t"] = td.Coefficient.str.replace("ev_", "")
    td["lo"] = td["Estimate"] - 1.96 * td["Std. Error"]
    td["hi"] = td["Estimate"] + 1.96 * td["Std. Error"]
    td[["t", "Estimate", "Std. Error", "Pr(>|t|)", "lo", "hi"]].round(4).to_csv(
        "output/tables/tab_v2_event_study.csv", index=False)
    print("\nEvent study (Panel A, dplan x quarter):")
    print(td[["t", "Estimate", "Std. Error", "Pr(>|t|)"]].round(3).to_string(index=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 150, "font.size": 9})
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.errorbar(range(len(td)), td["Estimate"],
                yerr=[td["Estimate"] - td.lo, td.hi - td["Estimate"]],
                marker="o", ms=4, capsize=2.5, lw=1, color="#4C72B0", ecolor="lightgray")
    ax.axhline(0, color="gray", lw=.8)
    ax.axvline(1.5, color="crimson", ls="--", lw=1, label="W2 regime starts (2022Q1)")
    ax.axvline(6.5, color="darkorange", ls="--", lw=1, label="W3 regime starts (2023Q2)")
    ax.set_xticks(range(len(td))); ax.set_xticklabels(td.t, rotation=90, fontsize=7)
    ax.set_ylabel("coef. on $\\Delta$planned remote $\\times$ quarter")
    ax.set_title("Panel A event study (two breaks)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig("output/figures/fig_v2_event_study.png", bbox_inches="tight")
    plt.close()
    print("saved fig_v2_event_study.png")


def longdiff_v2():
    """Wave-to-wave long differences from microdata: W1->W2 and W2->W3."""
    cw = pd.read_csv("data/processed/gswa_micro_country_wave.csv").rename(
        columns={"wfh_actual": "actual", "wfh_employer_plan": "plan",
                 "wfh_worker_desire": "desire"})
    w3 = pd.read_csv("data/processed/wfh_w3_gswa.csv").rename(
        columns={"wfh_actual": "actual", "wfh_employer_plan": "plan",
                 "wfh_worker_desire": "desire"})
    w3["wave"] = 3
    cw = pd.concat([cw[["iso3", "wave", "actual", "plan", "desire"]], w3[["iso3", "wave", "actual", "plan", "desire"]]])

    def wave_val(iso3, w, col):
        r = cw[(cw.iso3 == iso3) & (cw.wave == w)]
        return r[col].iloc[0] if len(r) else np.nan

    import itertools
    countries = sorted(set(cw.iso3))
    rows = []
    for i, j in itertools.product(countries, countries):
        if i == j:
            continue
        rows.append({
            "iso3_o": i, "iso3_d": j,
            "d_plan_12": (wave_val(j, 2, "plan") + wave_val(i, 2, "plan")) / 2
                         - (wave_val(j, 1, "plan") + wave_val(i, 1, "plan")) / 2,
            "d_plan_23": (wave_val(j, 3, "plan") + wave_val(i, 3, "plan")) / 2
                         - (wave_val(j, 2, "plan") + wave_val(i, 2, "plan")) / 2,
            "d_actual_23": (wave_val(j, 3, "actual") + wave_val(i, 3, "actual")) / 2
                           - (wave_val(j, 2, "actual") + wave_val(i, 2, "actual")) / 2,
            "d_plan_o_23": wave_val(i, 3, "plan") - wave_val(i, 2, "plan"),
            "d_plan_d_23": wave_val(j, 3, "plan") - wave_val(j, 2, "plan"),
        })
    ld = pd.DataFrame(rows)

    # collaboration changes from GitHub panels
    pa = pd.read_csv("data/processed/panel_A_3wave.csv")
    pre12 = pa[pa.t.isin(["2021Q3", "2021Q4"])].groupby("pair").ln_collab.mean()
    w2m = pa[pa.t.isin(["2022Q1", "2022Q2", "2022Q3", "2022Q4"])].groupby("pair").ln_collab.mean()
    w3m = pa[pa.t.isin(["2023Q2", "2023Q3", "2023Q4"])].groupby("pair").ln_collab.mean()
    d12 = (w2m - pre12).rename("d_ln_collab_12").reset_index()
    d23 = (w3m - w2m).rename("d_ln_collab_23").reset_index()
    base = pa.drop_duplicates("pair")[["pair", "iso3_o", "iso3_d", "cult_dist", "inst_dist",
                                       "ln_dist", "tzdiff", "comlang_off"]]
    d12 = d12.merge(base, on="pair").merge(ld, on=["iso3_o", "iso3_d"]).dropna(
        subset=["d_plan_12"])
    d23 = d23.merge(base, on="pair").merge(ld, on=["iso3_o", "iso3_d"]).dropna(
        subset=["d_plan_23", "d_plan_o_23"])
    for dd in (d12, d23):
        dd["pairu"] = dd.apply(lambda r: "-".join(sorted([r.iso3_o, r.iso3_d])), axis=1)
        zc = (dd.cult_dist - dd.cult_dist.mean()) / dd.cult_dist.std(ddof=0)
        zi = (dd.inst_dist - dd.inst_dist.mean()) / dd.inst_dist.std(ddof=0)
        dd["plan_x_cult"] = dd.d_plan_12 * zc if "12" in dd.columns[-6:] else dd.d_plan_23 * zc
    d12["plan_x_cult"] = d12.d_plan_12 * (d12.cult_dist - d12.cult_dist.mean()) / d12.cult_dist.std(ddof=0)
    d12["plan_x_inst"] = d12.d_plan_12 * (d12.inst_dist - d12.inst_dist.mean()) / d12.inst_dist.std(ddof=0)
    d23["plan_x_cult"] = d23.d_plan_23 * (d23.cult_dist - d23.cult_dist.mean()) / d23.cult_dist.std(ddof=0)
    d23["plan_x_inst"] = d23.d_plan_23 * (d23.inst_dist - d23.inst_dist.mean()) / d23.inst_dist.std(ddof=0)
    d23["actual_x_cult"] = d23.d_actual_23 * (d23.cult_dist - d23.cult_dist.mean()) / d23.cult_dist.std(ddof=0)
    d12.to_csv("data/processed/longdiff_v2_w12.csv", index=False)
    d23.to_csv("data/processed/longdiff_v2_w23.csv", index=False)

    print("\nLD W1->W2 (2021->2022, Panel A countries):")
    f1 = pf.feols("d_ln_collab_12 ~ d_plan_12 + plan_x_cult + ln_dist + tzdiff + comlang_off",
                  data=d12, vcov={"CRV1": "pairu"})
    print(f1.tidy().round(4).to_string())
    print("\nLD W2->W3 (2022->2023, Panel A countries):")
    for f in ["d_ln_collab_23 ~ d_plan_o_23 + d_plan_d_23",
              "d_ln_collab_23 ~ d_plan_o_23 + d_plan_d_23 + plan_x_cult",
              "d_ln_collab_23 ~ d_plan_o_23 + d_plan_d_23 + plan_x_cult + ln_dist + tzdiff + comlang_off",
              "d_ln_collab_23 ~ d_plan_o_23 + d_plan_d_23 + plan_x_inst + ln_dist + tzdiff + comlang_off"]:
        m = pf.feols(f, data=d23, vcov={"CRV1": "pairu"})
        print("--", f[:60])
        print(m.tidy().round(4).to_string())
    d23[["pair", "d_ln_collab_23", "d_plan_o_23", "d_plan_d_23", "d_plan_23", "plan_x_cult",
         "plan_x_inst"]].to_csv("output/tables/tab_v2_longdiff_w23.csv", index=False)
    return d12, d23


if __name__ == "__main__":
    import os
    os.makedirs("output/tables", exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "es":
        event_study_a()
    elif len(sys.argv) > 1 and sys.argv[1] == "ld":
        longdiff_v2()
    elif len(sys.argv) > 1 and sys.argv[1] == "pa":
        run_panel("data/processed/panel_A_3wave.csv", "panelA")
    elif len(sys.argv) > 1 and sys.argv[1] == "pb":
        run_panel("data/processed/panel_B_2wave.csv", "panelB")
    else:
        for args in ("pa", "pb", "es", "ld"):
            subprocess.run([sys.executable, "-X", "utf8", __file__, args], check=True)
