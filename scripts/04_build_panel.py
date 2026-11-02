"""Build the bilateral country-pair x quarter panel dataset.

Remote-work mapping: G-SWA W1+W2 pooled (fielded mid-2021 & early-2022) applies
2021Q3..2023Q1; W3 (fielded Apr-May 2023) applies 2023Q2..2023Q4.
Sample: directed pairs among G-SWA countries with W1W2 and W3 values.
"""
import pandas as pd
import numpy as np

HOF_DIMS = ["pdi", "idv", "mas", "uai", "ltowvs", "ivr"]
WGI_DIMS = ["wgi_va", "wgi_pv", "wgi_ge", "wgi_rq", "wgi_rl", "wgi_cc"]


def kogut_singh(df, cols):
    """Kogut-Singh (1988) distance: mean over dims of squared standardized differences."""
    z = (df[cols] - df[cols].mean()) / df[cols].std(ddof=0)
    return z


def build():
    # --- country codes: iso2 (GitHub) <-> iso3 (everything else)
    wbc = pd.read_csv("data/raw/controls/country_codes_worldbank.csv")
    iso2_to_iso3 = dict(zip(wbc.iso2, wbc.iso3))
    iso2_to_iso3.update({"XK": "XKX", "TW": "TWN"})  # Kosovo; Taiwan not in WB list
    name_to_iso3_wb = {}
    wgi = pd.read_csv("data/processed/governance_wgi_clean.csv").set_index("iso3")

    hof = pd.read_csv("data/processed/culture_dims_hofstede_iso3.csv").set_index("iso3")

    # --- remote work country panel
    w12 = pd.read_csv("data/raw/archive/wfh_w1w2_nber_table.csv").set_index("iso3")
    w3 = pd.read_csv("data/processed/wfh_w3_gswa.csv").set_index("iso3")
    common = sorted(set(w12.index) & set(w3.index))
    print(f"G-SWA countries with both waves: {len(common)}: {common}")
    remote_long = []
    quarters = [(y, q) for y in (2021, 2022, 2023) for q in (1, 2, 3, 4)]
    for (y, q) in quarters:
        use_w3 = (y, q) >= (2023, 2)
        for c in common:
            src = w3 if use_w3 else w12
            remote_long.append({
                "iso3": c, "year": y, "quarter": q,
                "remote": src.loc[c, "wfh_actual"],
                "remote_plan": src.loc[c, "wfh_employer_plan"],
                "remote_desire": src.loc[c, "wfh_worker_desire"],
                "wave": "W3" if use_w3 else "W1W2",
            })
    remote = pd.DataFrame(remote_long)

    # --- GitHub bilateral DV (directed), drop aggregates & territories & domestic
    ec = pd.read_csv("data/raw/dependent/collaborators_github.csv").dropna(subset=["source", "destination"])
    ec = ec[~ec.source.isin(["EU"]) & ~ec.destination.isin(["EU"])]
    ec["iso3_o"] = ec.source.map(iso2_to_iso3)
    ec["iso3_d"] = ec.destination.map(iso2_to_iso3)
    keep = set(common)
    ec = ec[ec.iso3_o.isin(keep) & ec.iso3_d.isin(keep) & (ec.iso3_o != ec.iso3_d)]
    ec = ec[((ec.year == 2021) & (ec.quarter >= 3)) | (ec.year > 2021)]
    ec = ec[ec.year <= 2023]
    ec = ec.rename(columns={"weight": "collaborators"})[
        ["iso3_o", "iso3_d", "year", "quarter", "collaborators"]]
    print(f"GitHub DV rows: {len(ec)}, pairs: {ec.groupby(['iso3_o','iso3_d']).ngroups}")

    # --- developers per country-quarter (size control)
    dev = pd.read_csv("data/raw/controls/developers_github.csv").dropna(subset=["iso2_code"])
    dev["iso3"] = dev.iso2_code.map(iso2_to_iso3)
    dev = dev.rename(columns={"developers": "developers"})[["iso3", "year", "quarter", "developers"]]

    # --- country-year controls from WDI (interpolate to quarters)
    wdi = pd.read_csv("data/raw/controls/macro_wdi_worldbank.csv")
    wdi = wdi[wdi.iso3.isin(keep)]
    wdi["ln_gdp"] = np.log(wdi.gdp_const2015usd)
    wdi["ln_gdppc"] = np.log(wdi.gdppc_const2015usd)
    # forward/backfill GDP years to panel quarters (2021-2023)
    qmap = {(2021, q): 2021 for q in (3, 4)}
    qmap.update({(2022, q): 2022 for q in (1, 2, 3, 4)})
    qmap.update({(2023, 1): 2022, (2023, 2): 2023, (2023, 3): 2023, (2023, 4): 2023})
    ctrl_rows = []
    for c in keep:
        for (y, q), yr in qmap.items():
            r = wdi[wdi.iso3 == c]
            # carry latest available year <= yr
            for yy in [yr, yr - 1, yr - 2]:
                rr = r[r.year == yy]
                if len(rr) and not np.isnan(rr.ln_gdp.iloc[0]):
                    ctrl_rows.append({"iso3": c, "year": y, "quarter": q, "ctrl_year": yy,
                                      "ln_gdp": rr.ln_gdp.iloc[0], "ln_gdppc": rr.ln_gdppc.iloc[0],
                                      "broadband": rr.broadband_per100.iloc[0]})
                    break
    ctrl = pd.DataFrame(ctrl_rows)

    # --- merge into pair-quarter panel
    panel = ec.merge(remote.rename(columns={
        "iso3": "iso3_o", "remote": "remote_o", "remote_plan": "remote_plan_o",
        "remote_desire": "remote_desire_o", "wave": "wave_o"}),
        on=["iso3_o", "year", "quarter"], how="left")
    panel = panel.merge(remote.rename(columns={
        "iso3": "iso3_d", "remote": "remote_d", "remote_plan": "remote_plan_d",
        "remote_desire": "remote_desire_d", "wave": "wave_d"}),
        on=["iso3_d", "year", "quarter"], how="left")
    panel = panel.merge(ctrl.rename(columns={
        "iso3": "iso3_o", "ln_gdp": "ln_gdp_o", "ln_gdppc": "ln_gdppc_o",
        "broadband": "broadband_o"}), on=["iso3_o", "year", "quarter"], how="left")
    panel = panel.merge(ctrl.rename(columns={
        "iso3": "iso3_d", "ln_gdp": "ln_gdp_d", "ln_gdppc": "ln_gdppc_d",
        "broadband": "broadband_d"}), on=["iso3_d", "year", "quarter"], how="left")
    panel = panel.merge(dev.rename(columns={"iso3": "iso3_o", "developers": "developers_o"}),
                        on=["iso3_o", "year", "quarter"], how="left")
    panel = panel.merge(dev.rename(columns={"iso3": "iso3_d", "developers": "developers_d"}),
                        on=["iso3_d", "year", "quarter"], how="left")

    # --- bilateral gravity controls
    grav = pd.read_csv("data/processed/gravity_cepii_bilateral.csv")
    grav = grav.rename(columns={"iso3_o": "iso3_o", "iso3_d": "iso3_d"})
    panel = panel.merge(grav, on=["iso3_o", "iso3_d"], how="left")

    # --- Kogut-Singh cultural distance (Hofstede) and institutional distance (WGI)
    def pair_distance(row_cols):
        pass
    # Kogut-Singh: standardize against the FULL reference sample (all countries with
    # data), not the estimation sample, then evaluate for panel countries
    zs_hof = kogut_singh(hof, HOF_DIMS)
    zs_wgi = kogut_singh(wgi, WGI_DIMS)
    dist_rows = []
    for i in common:
        for j in common:
            if i == j:
                continue
            row = {"iso3_o": i, "iso3_d": j}
            if i in zs_hof.index and j in zs_hof.index:
                d = ((zs_hof.loc[i] - zs_hof.loc[j]) ** 2).mean()
                row["cult_dist"] = float(d)
            if i in zs_wgi.index and j in zs_wgi.index:
                d = ((zs_wgi.loc[i] - zs_wgi.loc[j]) ** 2).mean()
                row["inst_dist"] = float(d)
            dist_rows.append(row)
    dists = pd.DataFrame(dist_rows)
    panel = panel.merge(dists, on=["iso3_o", "iso3_d"], how="left")

    # --- composite distance: mean of the two standardized across pairs
    dm = dists.copy()
    dm["cult_z"] = (dm.cult_dist - dm.cult_dist.mean()) / dm.cult_dist.std(ddof=0)
    dm["inst_z"] = (dm.inst_dist - dm.inst_dist.mean()) / dm.inst_dist.std(ddof=0)
    dm["dist_z"] = dm[["cult_z", "inst_z"]].mean(axis=1)
    panel = panel.merge(dm[["iso3_o", "iso3_d", "dist_z"]], on=["iso3_o", "iso3_d"], how="left")

    # --- derived regressors
    panel["t"] = panel.year.astype(str) + "Q" + panel.quarter.astype(str)
    panel["pair"] = panel.iso3_o + "-" + panel.iso3_d
    panel["remote_ij"] = (panel.remote_o + panel.remote_d) / 2
    panel["ln_collab"] = np.log1p(panel.collaborators)
    panel["ln_dist"] = np.log(panel.dist)
    panel["ln_dev_o"] = np.log(panel.developers_o)
    panel["ln_dev_d"] = np.log(panel.developers_d)
    # cross-border intensity: course question is a shift "from domestic to
    # cross-border" -> collaboration per domestic developer stock
    panel["collab_int_o"] = panel.collaborators / panel.developers_o
    panel["collab_int_d"] = panel.collaborators / panel.developers_d
    panel["ln_int_o"] = panel.ln_collab - panel.ln_dev_o
    panel["ln_int_d"] = panel.ln_collab - panel.ln_dev_d

    # interactions (with standardized distances for readability)
    for d in ["cult_dist", "inst_dist", "dist_z"]:
        dz = (panel[d] - panel[d].mean()) / panel[d].std(ddof=0)
        panel[f"remote_x_{d}"] = panel.remote_ij * dz

    panel.to_csv("data/processed/panel_pair_quarter.csv", index=False)
    print("saved data/processed/panel_pair_quarter.csv", panel.shape)
    print("countries:", len(common), "quarters:", panel.t.nunique(),
          "pairs:", panel.pair.nunique())
    print(panel[["collaborators", "remote_o", "remote_d", "cult_dist", "inst_dist"]].describe().round(2))
    return panel


if __name__ == "__main__":
    import os
    os.makedirs("data/processed", exist_ok=True)
    build()
