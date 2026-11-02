"""Appendix C: Hofstede dimension scores for the Panel A sample + heatmap figure."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.rcParams.update({"figure.dpi": 150, "font.size": 9})

DIMS = {"pdi": "Power\nDistance", "idv": "Individual-\nism", "mas": "Masculinity",
        "uai": "Uncertainty\nAvoidance", "ltowvs": "Long-Term\nOrientation", "ivr": "Indulgence"}
PANEL_A = ["AUS", "CAN" if False else "CHN", "DEU", "ESP" if False else "FRA", "GBR", "GRC",
           "HUN", "NLD", "POL", "SWE", "USA"]
NAMES = {"AUS": "Australia", "CHN": "China", "DEU": "Germany", "FRA": "France",
         "GBR": "United Kingdom", "GRC": "Greece", "HUN": "Hungary", "NLD": "Netherlands",
         "POL": "Poland", "SWE": "Sweden", "USA": "United States"}


def main():
    hof = pd.read_csv("data/raw/hofstede_clean.csv").set_index("iso3")
    sub = hof.loc[[c for c in PANEL_A if c in hof.index], list(DIMS)]
    sub.to_csv("output/tables/tab_hofstede_dims_panelA.csv")
    print(sub.to_string())

    # z-standardize against the full reference sample
    full = hof[list(DIMS)]
    z = (sub - full.mean()) / full.std(ddof=0)

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    im = ax.imshow(z.values, cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(DIMS)))
    ax.set_xticklabels(list(DIMS.values()), fontsize=8)
    ax.set_yticks(range(len(sub)))
    ax.set_yticklabels([f"{NAMES[c]} ({c})" for c in sub.index], fontsize=8)
    for i in range(sub.shape[0]):
        for j in range(sub.shape[1]):
            ax.text(j, i, f"{sub.values[i, j]:.0f}", ha="center", va="center",
                    fontsize=7.5, color="black")
    cb = fig.colorbar(im, ax=ax, shrink=.85)
    cb.set_label("z-score vs. full reference sample", fontsize=8)
    ax.set_title("Hofstede dimension scores, Panel A economies (0-100 scale)", fontsize=10)
    plt.tight_layout()
    plt.savefig("paper/figures/fig_hofstede_dims.png", bbox_inches="tight")
    plt.close()
    print("saved fig_hofstede_dims.png and tab_hofstede_dims_panelA.csv")


if __name__ == "__main__":
    main()
