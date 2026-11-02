"""Descriptive statistics and figures."""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

VARS = {
    "collaborators": "Cross-border collaborators (count)",
    "ln_collab": "ln(1 + collaborators)",
    "remote_o": "Remote-work intensity, origin (WFH days/wk)",
    "remote_d": "Remote-work intensity, destination (WFH days/wk)",
    "remote_ij": "Remote-work intensity, pair mean",
    "cult_dist": "Cultural distance (Kogut-Singh, Hofstede)",
    "inst_dist": "Institutional distance (Kogut-Singh, WGI)",
    "dist_z": "Composite distance (z)",
    "ln_gdp_o": "ln GDP, origin",
    "ln_gdp_d": "ln GDP, destination",
    "ln_gdppc_o": "ln GDP p.c., origin",
    "broadband_o": "Broadband per 100, origin",
    "ln_dist": "ln geodesic distance",
    "tzdiff": "Time-zone difference (hrs)",
    "comlang_off": "Common official language",
    "contig": "Contiguity",
    "developers_o": "GitHub developers, origin",
    "developers_d": "GitHub developers, destination",
}


def summary_table(p):
    rows = []
    for v, label in VARS.items():
        s = p[v].dropna()
        rows.append({"Variable": label, "N": int(s.count()), "Mean": s.mean(),
                     "Std.Dev.": s.std(), "Min": s.min(), "p25": s.quantile(.25),
                     "Median": s.median(), "p75": s.quantile(.75), "Max": s.max()})
    t = pd.DataFrame(rows)
    t.iloc[:, 1:] = t.iloc[:, 1:].round(2)
    os.makedirs("output/tables", exist_ok=True)
    t.to_csv("output/tables/tab1_summary_stats.csv", index=False)
    print(t.to_string(index=False))
    return t


def fig_trends(p):
    os.makedirs("output/figures", exist_ok=True)
    # (a) aggregate collaboration over quarters
    agg = p.groupby("t")[["collaborators"]].sum().reset_index()
    agg["t"] = pd.Categorical(agg.t, categories=sorted(p.t.unique()), ordered=True)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    axes[0].plot(agg.t.astype(str), agg.collaborators / 1e6, marker="o", ms=3)
    axes[0].set_title("(a) Total cross-border collaborators")
    axes[0].set_ylabel("millions")
    axes[0].tick_params(axis="x", rotation=90, labelsize=6.5)
    # (b) remote work trend (country examples + mean)
    w12 = pd.read_csv("data/raw/archive/wfh_w1w2_nber_table.csv").set_index("iso3")
    w3 = pd.read_csv("data/processed/wfh_w3_gswa.csv").set_index("iso3")
    countries = ["USA", "GBR", "DEU", "JPN", "KOR", "IND"] if "IND" in w12.index else \
        ["USA", "GBR", "DEU", "JPN", "KOR", "CAN"]
    xs = list(range(len(agg)))
    for c in countries:
        v12 = w12.loc[c, "wfh_actual"] if c in w12.index else None
        v3 = w3.loc[c, "wfh_actual"] if c in w3.index else None
        if v12 is None or v3 is None:
            continue
        ys = [v12] * 7 + [v3] * 3
        axes[1].plot(xs, ys, marker=".", ms=2, label=c, alpha=.8)
    axes[1].axvline(6.5, color="gray", ls="--", lw=.8)
    axes[1].set_xticks(xs[::2]); axes[1].set_xticklabels([str(x) for x in agg.t][::2], rotation=90, fontsize=6.5)
    axes[1].legend(fontsize=6, ncol=2); axes[1].set_title("(b) Remote-work days/week (G-SWA)")
    axes[1].set_ylabel("WFH full days per week")
    # (c) distribution of collaborators
    axes[2].hist(np.log10(p.collaborators), bins=40, color="#4C72B0")
    axes[2].set_title("(c) Distribution of pair collaboration")
    axes[2].set_xlabel("log10(collaborators)")
    plt.tight_layout()
    plt.savefig("output/figures/fig1_trends.png", bbox_inches="tight")
    plt.close()
    print("saved fig1_trends.png")


def fig_distance(p):
    # pair-level cross-section: average collaboration vs cultural/institutional distance
    pl = p.groupby(["pair", "cult_dist", "inst_dist", "comlang_off", "ln_dist"]).agg(
        collaborators=("collaborators", "mean")).reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    axes[0].scatter(pl.cult_dist, np.log10(pl.collaborators), s=8, alpha=.5)
    b, a = np.polyfit(pl.cult_dist, np.log10(pl.collaborators), 1)
    xs = np.linspace(pl.cult_dist.min(), pl.cult_dist.max(), 10)
    axes[0].plot(xs, a + b * xs, color="crimson", lw=1.2)
    axes[0].set_xlabel("Cultural distance (K-S)"); axes[0].set_ylabel("log10 mean collaborators")
    axes[0].set_title(f"(a) Cultural distance, slope={b:.2f}")
    axes[1].scatter(pl.inst_dist, np.log10(pl.collaborators), s=8, alpha=.5, color="seagreen")
    b, a = np.polyfit(pl.inst_dist, np.log10(pl.collaborators), 1)
    xs = np.linspace(pl.inst_dist.min(), pl.inst_dist.max(), 10)
    axes[1].plot(xs, a + b * xs, color="crimson", lw=1.2)
    axes[1].set_xlabel("Institutional distance (K-S)"); axes[1].set_ylabel("")
    axes[1].set_title(f"(b) Institutional distance, slope={b:.2f}")
    axes[2].scatter(pl.ln_dist, np.log10(pl.collaborators), s=8, alpha=.5, color="darkorange")
    b, a = np.polyfit(pl.ln_dist, np.log10(pl.collaborators), 1)
    xs = np.linspace(pl.ln_dist.min(), pl.ln_dist.max(), 10)
    axes[2].plot(xs, a + b * xs, color="crimson", lw=1.2)
    axes[2].set_xlabel("ln geodesic distance"); axes[2].set_ylabel("")
    axes[2].set_title(f"(c) Geographic distance, slope={b:.2f}")
    plt.tight_layout()
    plt.savefig("output/figures/fig2_distance_scatter.png", bbox_inches="tight")
    plt.close()
    print("saved fig2_distance_scatter.png")


def fig_toppairs(p):
    top = p.groupby("pair").collaborators.mean().sort_values(ascending=False).head(15)[::-1]
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.barh(top.index, top.values / 1000, color="#4C72B0")
    ax.set_xlabel("mean collaborators (thousands)")
    ax.set_title("Top-15 country pairs by mean cross-border collaboration")
    plt.tight_layout()
    plt.savefig("output/figures/fig3_top_pairs.png", bbox_inches="tight")
    plt.close()
    print("saved fig3_top_pairs.png")


if __name__ == "__main__":
    p = pd.read_csv("data/processed/panel_pair_quarter.csv")
    summary_table(p)
    fig_trends(p)
    fig_distance(p)
    fig_toppairs(p)
