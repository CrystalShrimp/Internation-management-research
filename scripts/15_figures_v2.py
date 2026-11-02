"""v2 figures: G-SWA waves from microdata, LD marginal effects, EWCS validation."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import pyfixest as pf

plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

WAVE_LABEL = {1: "W1 (Jul-Aug 2021)", 2: "W2 (Jan-Feb 2022)", 3: "W3 (Apr-May 2023)"}


def fig_waves():
    micro = pd.read_csv("data/processed/gswa_micro_country_wave.csv").rename(
        columns={"wfh_actual": "actual", "wfh_employer_plan": "plan"})
    w3 = pd.read_csv("data/raw/gswa_w3.csv").rename(
        columns={"wfh_actual": "actual", "wfh_employer_plan": "plan"})
    w3["wave"] = 3
    cw = pd.concat([micro[["iso3", "wave", "actual", "plan"]],
                    w3[["iso3", "wave", "actual", "plan"]]])

    show = ["USA", "GBR", "DEU", "JPN", "KOR", "CHN", "SWE", "FRA", "AUS", "SGP"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    xs = [1, 2, 3]
    for ax, var, title in [(axes[0], "plan", "(a) Employer-planned WFH days/week"),
                           (axes[1], "actual", "(b) Actual WFH days, survey week")]:
        for c in show:
            g = cw[cw.iso3 == c].sort_values("wave")
            if g[var].notna().sum() < 2:
                continue
            ax.plot(g.wave, g[var], marker="o", ms=3, lw=1, label=c, alpha=.85)
        ax.set_xticks(xs)
        ax.set_xticklabels(["W1\n2021", "W2\n2022", "W3\n2023"])
        ax.set_title(title)
        ax.set_ylabel("WFH full days per week" if var == "plan" else "")
    axes[1].legend(fontsize=6.5, ncol=2)
    plt.tight_layout()
    plt.savefig("paper/figures/fig_waves.png", bbox_inches="tight")
    plt.close()
    print("saved fig_waves.png")


def fig_marginal():
    d = pd.read_csv("data/processed/longdiff_v2_w23.csv")
    m = pf.feols("d_ln_collab_23 ~ d_plan_o_23 + d_plan_d_23 + plan_x_cult + ln_dist + tzdiff + comlang_off",
                 data=d, vcov={"CRV1": "pairu"})
    t = m.tidy()
    b_plan = (t.loc["d_plan_o_23", "Estimate"] + t.loc["d_plan_d_23", "Estimate"]) / 2
    b_x = t.loc["plan_x_cult", "Estimate"]
    se_plan = (t.loc["d_plan_o_23", "Std. Error"] + t.loc["d_plan_d_23", "Std. Error"]) / 2
    se_x = t.loc["plan_x_cult", "Std. Error"]
    zs = np.linspace(-1.6, 2.6, 41)
    me = b_plan + b_x * zs
    se = np.sqrt(se_plan**2 + (zs * se_x)**2)
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    ax.plot(zs, me, color="#4C72B0", lw=1.5)
    ax.fill_between(zs, me - 1.96 * se, me + 1.96 * se, alpha=.2, color="#4C72B0")
    ax.axhline(0, color="gray", lw=.8)
    ax.set_xlabel("Bilateral Hofstede cultural distance (z)")
    ax.set_ylabel("Effect of +1 planned WFH day\non $\\Delta$ln(collaboration) 2022$\\to$2023")
    ax.set_title("Marginal effect by cultural distance (long difference)")
    plt.tight_layout()
    plt.savefig("paper/figures/fig_marginal_v2.png", bbox_inches="tight")
    plt.close()
    print(f"saved fig_marginal_v2.png; ME at z=-1: {b_plan-b_x:+.3f}, z=+1: {b_plan+b_x:+.3f}")


def fig_ewcs():
    tw = pd.read_csv("data/processed/ewcs_telework.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    s = tw.sort_values("telework_any_pct")
    axes[0].barh(s.iso2, s.telework_any_pct, color="#4C72B0")
    axes[0].set_xlabel("% employees with any telework (EWCS/EWCTS 2021)")
    axes[0].set_title("(a) EWCS telework intensity by country")
    axes[0].tick_params(labelsize=6)
    cw = pd.read_csv("data/processed/gswa_micro_country_wave.csv")
    w2 = cw[cw.wave == 2].set_index("iso3")
    tw2 = tw.set_index("iso3")
    common = tw2.index.intersection(w2.index)
    axes[1].scatter(w2.loc[common, "wfh_employer_plan"], tw2.loc[common, "telework_any_pct"],
                    s=30, color="crimson", alpha=.8)
    for c in common:
        axes[1].annotate(c, (w2.loc[c, "wfh_employer_plan"], tw2.loc[c, "telework_any_pct"]),
                         fontsize=7, xytext=(3, 3), textcoords="offset points")
    r = np.corrcoef(w2.loc[common, "wfh_employer_plan"], tw2.loc[common, "telework_any_pct"])[0, 1]
    axes[1].set_xlabel("G-SWA planned WFH days (W2, 2022)")
    axes[1].set_ylabel("EWCS % any telework (2021)")
    axes[1].set_title(f"(b) Cross-survey validation (r = {r:.2f}, n = {len(common)})")
    plt.tight_layout()
    plt.savefig("paper/figures/fig_ewcs.png", bbox_inches="tight")
    plt.close()
    print("saved fig_ewcs.png")


if __name__ == "__main__":
    fig_waves()
    fig_marginal()
    fig_ewcs()
