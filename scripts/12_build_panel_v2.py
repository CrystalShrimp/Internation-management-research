"""Build v2 panels from G-SWA microdata country-wave aggregates (W1, W2) plus the
official Wave 3 summary (wfhresearch.com GSWA-Figures-Data-2023.xlsx).

Wave -> quarter mapping (fielding dates):
  W1 (Jul-Aug 2021) -> 2021Q3-2021Q4
  W2 (Jan-Feb 2022) -> 2022Q1-2023Q1
  W3 (Apr-May 2023) -> 2023Q2-2023Q4

Panels:
  A (3-regime balanced): countries in all three waves, 2021Q3-2023Q4
  B (2-regime extended): countries in W2 & W3, 2022Q1-2023Q4
"""
from pathlib import Path
import pandas as pd
import numpy as np

HOF_DIMS = ["pdi", "idv", "mas", "uai", "ltowvs", "ivr"]
WGI_DIMS = ["wgi_va", "wgi_pv", "wgi_ge", "wgi_rq", "wgi_rl", "wgi_cc"]
CONTROLS = ["ln_dev_o", "ln_dev_d", "ln_gdp_o", "ln_gdp_d", "broadband_o", "broadband_d"]

REGIME = {(2021, 3): 1, (2021, 4): 1,
          (2022, 1): 2, (2022, 2): 2, (2022, 3): 2, (2022, 4): 2, (2023, 1): 2,
          (2023, 2): 3, (2023, 3): 3, (2023, 4): 3}


def country_wave_remote():
    micro = pd.read_csv("data/processed/gswa_micro_country_wave.csv")
    micro = micro.rename(columns={"wfh_actual": "actual", "wfh_employer_plan": "plan",
                                  "wfh_worker_desire": "desire"})
    micro["wave"] = micro.wave.astype(int)
    w3 = pd.read_csv("data/raw/gswa_w3.csv")[["iso3", "wfh_actual", "wfh_employer_plan",
                                              "wfh_worker_desire"]]
    w3 = w3.rename(columns={"wfh_actual": "actual", "wfh_employer_plan": "plan",
                            "wfh_worker_desire": "desire"})
    w3["wave"] = 3
    return pd.concat([micro[["iso3", "wave", "actual", "plan", "desire", "n"]], w3], ignore_index=True)


def build_panel(countries, quarters):
    cw = country_wave_remote()
    have = cw[cw.iso3.isin(countries)]
    remote_rows = []
    for c in countries:
        for (y, q) in quarters:
            w = REGIME[(y, q)]
            r = have[(have.iso3 == c) & (have.wave == w)]
            if len(r):
                remote_rows.append({"iso3": c, "year": y, "quarter": q,
                                    "remote": r.actual.iloc[0], "remote_plan": r.plan.iloc[0],
                                    "remote_desire": r.desire.iloc[0], "wave": w})
    remote = pd.DataFrame(remote_rows)

    wbc = pd.read_csv("data/raw/wb_countries.csv")
    iso2_to_iso3 = dict(zip(wbc.iso2, wbc.iso3)) | {"XK": "XKX", "TW": "TWN"}
    ec = pd.read_csv("data/raw/economy_collaborators.csv").dropna(subset=["source", "destination"])
    ec = ec[~ec.source.isin(["EU"]) & ~ec.destination.isin(["EU"])]
    ec["iso3_o"] = ec.source.map(iso2_to_iso3)
    ec["iso3_d"] = ec.destination.map(iso2_to_iso3)
    keep = set(countries)
    ec = ec[ec.iso3_o.isin(keep) & ec.iso3_d.isin(keep) & (ec.iso3_o != ec.iso3_d)]
    ec = ec[ec.year.notna() & ec.quarter.notna()]
    ec["year"] = ec.year.astype(int); ec["quarter"] = ec.quarter.astype(int)
    qq = pd.DataFrame(quarters, columns=["year", "quarter"])
    ec = ec.merge(qq, on=["year", "quarter"])
    ec = ec.rename(columns={"weight": "collaborators"})

    dev = pd.read_csv("data/raw/developers.csv").dropna(subset=["iso2_code"])
    dev["iso3"] = dev.iso2_code.map(iso2_to_iso3)
    wdi = pd.read_csv("data/raw/worldbank_wgi_wdi.csv")
    wdi["ln_gdp"] = np.log(wdi.gdp_const2015usd)
    wdi["ln_gdppc"] = np.log(wdi.gdppc_const2015usd)

    # balanced frame: directed pairs x quarters, zero-filled
    import itertools
    pairs = pd.DataFrame([(i, j) for i in countries for j in countries if i != j],
                         columns=["iso3_o", "iso3_d"])
    panel = pd.DataFrame(list(itertools.product(pairs.itertuples(index=False), quarters)),
                         columns=["pair_t", "yq"])
    panel[["iso3_o", "iso3_d"]] = pd.DataFrame(panel.pair_t.tolist(), index=panel.index)
    panel[["year", "quarter"]] = pd.DataFrame(panel.yq.tolist(), index=panel.index)
    panel = panel.drop(columns=["pair_t", "yq"]).merge(
        ec[["iso3_o", "iso3_d", "year", "quarter", "collaborators"]],
        on=["iso3_o", "iso3_d", "year", "quarter"], how="left")
    panel["collaborators"] = panel.collaborators.fillna(0)
    panel["ln_collab"] = np.log1p(panel.collaborators)

    w = wdi.set_index(["iso3", "year"])
    def wdi_lookup(c, yy, col):
        for ytry in (yy, yy - 1, yy - 2):
            if (c, ytry) in w.index:
                v = w.loc[(c, ytry), col]
                if not np.isnan(v):
                    return v
        return np.nan

    for s in ["o", "d"]:
        panel = panel.merge(
            remote.rename(columns={"iso3": f"iso3_{s}", "remote": f"remote_{s}",
                                   "remote_plan": f"remote_plan_{s}",
                                   "remote_desire": f"remote_desire_{s}",
                                   "wave": f"wave_{s}"}),
            on=[f"iso3_{s}", "year", "quarter"], how="left")
        panel = panel.merge(
            dev.rename(columns={"iso3": f"iso3_{s}", "developers": f"developers_{s}"}),
            on=[f"iso3_{s}", "year", "quarter"], how="left")
        panel[f"ln_dev_{s}"] = np.log(panel[f"developers_{s}"])
        ctrl_year = np.where(panel.year == 2021, 2021,
                             np.where(panel.year == 2022, 2022, 2023))
        panel[f"ln_gdp_{s}"] = [wdi_lookup(c, yy, "ln_gdp")
                                for c, yy in zip(panel[f"iso3_{s}"], ctrl_year)]
        panel[f"ln_gdppc_{s}"] = [wdi_lookup(c, yy, "ln_gdppc")
                                  for c, yy in zip(panel[f"iso3_{s}"], ctrl_year)]
        panel[f"broadband_{s}"] = [wdi_lookup(c, yy, "broadband_per100")
                                   for c, yy in zip(panel[f"iso3_{s}"], ctrl_year)]

    # distances: Kogut-Singh vs full reference sample
    hof = pd.read_csv("data/raw/hofstede_clean.csv").set_index("iso3")
    wgi = pd.read_csv("data/raw/wgi_clean.csv").set_index("iso3")
    zs_hof = (hof[HOF_DIMS] - hof[HOF_DIMS].mean()) / hof[HOF_DIMS].std(ddof=0)
    zs_wgi = (wgi[WGI_DIMS] - wgi[WGI_DIMS].mean()) / wgi[WGI_DIMS].std(ddof=0)
    drows = []
    for i in countries:
        for j in countries:
            if i == j:
                continue
            r = {"iso3_o": i, "iso3_d": j}
            if i in zs_hof.index and j in zs_hof.index and zs_hof.loc[i].notna().all() \
                    and zs_hof.loc[j].notna().all():
                r["cult_dist"] = float(((zs_hof.loc[i] - zs_hof.loc[j]) ** 2).mean())
            if i in zs_wgi.index and j in zs_wgi.index:
                r["inst_dist"] = float(((zs_wgi.loc[i] - zs_wgi.loc[j]) ** 2).mean())
            drows.append(r)
    dists = pd.DataFrame(drows)
    for d in ["cult_dist", "inst_dist"]:
        dists[f"{d[:4]}_z"] = (dists[d] - dists[d].mean()) / dists[d].std(ddof=0)
    dists["dist_z"] = dists[["cult_z", "inst_z"]].mean(axis=1)
    panel = panel.merge(dists, on=["iso3_o", "iso3_d"], how="left")

    grav = pd.read_csv("data/raw/cepii_bilateral.csv")
    panel = panel.merge(grav[["iso3_o", "iso3_d", "dist", "tzdiff", "comlang_off", "contig"]],
                        on=["iso3_o", "iso3_d"], how="left")
    panel["ln_dist"] = np.log(panel.dist)

    panel["t"] = panel.year.astype(str) + "Q" + panel.quarter.astype(str)
    panel["pair"] = panel.iso3_o + "-" + panel.iso3_d
    panel["remote_ij"] = (panel.remote_o + panel.remote_d) / 2
    panel["remote_plan_ij"] = (panel.remote_plan_o + panel.remote_plan_d) / 2
    panel["ln_int_o"] = panel.ln_collab - panel.ln_dev_o
    # interactions with standardized Hofstede cultural distance (course-designated
    # moderator) and WGI institutional distance (extension)
    for d, nm in [("cult_dist", "cult"), ("inst_dist", "inst")]:
        z = (panel[d] - panel[d].mean()) / panel[d].std(ddof=0)
        panel[f"plan_x_{nm}"] = panel.remote_plan_ij * z
        panel[f"remote_x_{nm}"] = panel.remote_ij * z
        panel[f"plan_o_x_{nm}"] = panel.remote_plan_o * z
        panel[f"plan_d_x_{nm}"] = panel.remote_plan_d * z
    return panel


if __name__ == "__main__":
    Path("data/processed").mkdir(exist_ok=True)
    Q_FULL = [(y, q) for y in (2021, 2022, 2023) for q in (1, 2, 3, 4)
              if (y, q) in REGIME]
    Q_B = [(y, q) for (y, q) in Q_FULL if REGIME[(y, q)] >= 2]

    cw = country_wave_remote()
    w1 = set(cw[cw.wave == 1].iso3); w2 = set(cw[cw.wave == 2].iso3); w3 = set(cw[cw.wave == 3].iso3)
    a_countries = sorted(w1 & w2 & w3)
    b_countries = sorted(w2 & w3)

    pa = build_panel(a_countries, Q_FULL)
    pa.to_csv("data/processed/panel_A_3wave.csv", index=False)
    print("Panel A:", pa.shape, "countries", len(a_countries), "pairs", pa.pair.nunique())
    pb = build_panel(b_countries, Q_B)
    pb.to_csv("data/processed/panel_B_2wave.csv", index=False)
    print("Panel B:", pb.shape, "countries", len(b_countries), "pairs", pb.pair.nunique())
    print("\nplanned WFH by regime (Panel A):")
    print(pa.groupby("wave_o")[["remote_plan_o", "remote_o"]].mean().round(2))
