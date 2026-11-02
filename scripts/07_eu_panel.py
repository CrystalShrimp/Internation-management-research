"""EU sub-sample: annual pair-year panel using Eurostat LFS WFH rates
(alternative telework measure; proposal's EWCS microdata requires registration,
Eurostat LFS 'Employed persons working from home' is the harmonised public source).

DV: annual sum of quarterly cross-border collaborators (GitHub Innovation Graph).
Remote: % employees usually or sometimes working from home (Eurostat LFSA_EHOMP).
"""
import os
import pandas as pd
import numpy as np
import pyfixest as pf

GEO_TO_ISO2 = {  # Eurostat geo -> GitHub iso2
    "BE": "BE", "BG": "BG", "CZ": "CZ", "DK": "DK", "DE": "DE", "EE": "EE", "IE": "IE",
    "EL": "GR", "ES": "ES", "FR": "FR", "HR": "HR", "IT": "IT", "CY": "CY", "LV": "LV",
    "LT": "LT", "LU": "LU", "HU": "HU", "MT": "MT", "NL": "NL", "AT": "AT", "PL": "PL",
    "PT": "PT", "RO": "RO", "SI": "SI", "SK": "SK", "FI": "FI", "SE": "SE",
    "IS": "IS", "NO": "NO", "CH": "CH", "UK": "GB", "RS": "RS",
}
HOF_DIMS = ["pdi", "idv", "mas", "uai", "ltowvs", "ivr"]
WGI_DIMS = ["wgi_va", "wgi_pv", "wgi_ge", "wgi_rq", "wgi_rl", "wgi_cc"]
CONTROLS = ["ln_dev_o", "ln_dev_d", "ln_gdp_o", "ln_gdp_d", "broadband_o", "broadband_d"]


def build_eu_panel():
    wbc = pd.read_csv("data/raw/controls/country_codes_worldbank.csv")
    iso2_to_iso3 = dict(zip(wbc.iso2, wbc.iso3))
    es = pd.read_csv("data/raw/archive/telework_eurostat_clean.csv")
    es = es[es.geo.isin(GEO_TO_ISO2) & es.year.between(2019, 2024)]
    es["iso3"] = es.geo.map(GEO_TO_ISO2).map(iso2_to_iso3)
    es = es.dropna(subset=["iso3", "wfh_ever_pct"])
    print("Eurostat countries:", es.iso3.nunique(), "years:", sorted(es.year.unique()))

    countries = sorted(es.iso3.unique())
    # DV: annual collaborators from GitHub (quarterly sum)
    ec = pd.read_csv("data/raw/dependent/collaborators_github.csv").dropna(subset=["source", "destination"])
    ec = ec[~ec.source.isin(["EU"]) & ~ec.destination.isin(["EU"])]
    ec["iso3_o"] = ec.source.map(iso2_to_iso3)
    ec["iso3_d"] = ec.destination.map(iso2_to_iso3)
    ec = ec[ec.iso3_o.isin(countries) & ec.iso3_d.isin(countries) & (ec.iso3_o != ec.iso3_d)]
    ann = ec.groupby(["iso3_o", "iso3_d", "year"], as_index=False).agg(
        collaborators=("weight", "sum"))

    # balanced frame: all directed pairs x all years, zeros where absent
    import itertools
    full = pd.DataFrame(itertools.product(countries, countries, range(2019, 2025)),
                        columns=["iso3_o", "iso3_d", "year"])
    full = full[full.iso3_o != full.iso3_d]
    panel = full.merge(ann, on=["iso3_o", "iso3_d", "year"], how="left")
    panel["collaborators"] = panel.collaborators.fillna(0)

    # remote + controls (country-year)
    esr = es.rename(columns={"iso3": "iso3_o", "wfh_ever_pct": "remote_o",
                             "wfh_usually_pct": "remote_usu_o"})[
        ["iso3_o", "year", "remote_o", "remote_usu_o"]]
    esr_d = es.rename(columns={"iso3": "iso3_d", "wfh_ever_pct": "remote_d",
                               "wfh_usually_pct": "remote_usu_d"})[
        ["iso3_d", "year", "remote_d", "remote_usu_d"]]
    panel = panel.merge(esr, on=["iso3_o", "year"], how="left")
    panel = panel.merge(esr_d, on=["iso3_d", "year"], how="left")
    panel = panel.dropna(subset=["remote_o", "remote_d"])  # need both endpoints' WFH

    wdi = pd.read_csv("data/raw/controls/macro_wdi_worldbank.csv")
    wdi["ln_gdp"] = np.log(wdi.gdp_const2015usd)
    wdi["ln_gdppc"] = np.log(wdi.gdppc_const2015usd)
    wdi = wdi[["iso3", "year", "ln_gdp", "ln_gdppc", "broadband_per100"]]
    for s in ["o", "d"]:
        panel = panel.merge(
            wdi.rename(columns={"iso3": f"iso3_{s}", "ln_gdp": f"ln_gdp_{s}",
                                "ln_gdppc": f"ln_gdppc_{s}",
                                "broadband_per100": f"broadband_{s}"}),
            on=[f"iso3_{s}", "year"], how="left")

    dev = pd.read_csv("data/raw/controls/developers_github.csv").dropna(subset=["iso2_code"])
    dev["iso3"] = dev.iso2_code.map(iso2_to_iso3)
    dev_ann = dev.groupby(["iso3", "year"], as_index=False).developers.mean()
    for s in ["o", "d"]:
        panel = panel.merge(
            dev_ann.rename(columns={"iso3": f"iso3_{s}", "developers": f"developers_{s}"}),
            on=[f"iso3_{s}", "year"], how="left")
    panel["ln_dev_o"] = np.log(panel.developers_o)
    panel["ln_dev_d"] = np.log(panel.developers_d)

    # distances (K-S) among panel countries
    hof = pd.read_csv("data/processed/culture_dims_hofstede_iso3.csv").set_index("iso3")
    wgi = pd.read_csv("data/processed/governance_wgi_clean.csv").set_index("iso3")
    cs = sorted(set(panel.iso3_o.unique()) & set(panel.iso3_d.unique()))
    zs_hof = (hof[HOF_DIMS] - hof[HOF_DIMS].mean()) / hof[HOF_DIMS].std(ddof=0)
    zs_wgi = (wgi[WGI_DIMS] - wgi[WGI_DIMS].mean()) / wgi[WGI_DIMS].std(ddof=0)
    rows = []
    for i in cs:
        for j in cs:
            if i == j:
                continue
            r = {"iso3_o": i, "iso3_d": j}
            if i in zs_hof.index and j in zs_hof.index:
                r["cult_dist"] = float(((zs_hof.loc[i] - zs_hof.loc[j]) ** 2).mean())
            if i in zs_wgi.index and j in zs_wgi.index:
                r["inst_dist"] = float(((zs_wgi.loc[i] - zs_wgi.loc[j]) ** 2).mean())
            rows.append(r)
    dists = pd.DataFrame(rows)
    dists["cult_z"] = (dists.cult_dist - dists.cult_dist.mean()) / dists.cult_dist.std(ddof=0)
    dists["inst_z"] = (dists.inst_dist - dists.inst_dist.mean()) / dists.inst_dist.std(ddof=0)
    dists["dist_z"] = dists[["cult_z", "inst_z"]].mean(axis=1)
    panel = panel.merge(dists, on=["iso3_o", "iso3_d"], how="left")

    grav = pd.read_csv("data/processed/gravity_cepii_bilateral.csv")
    panel = panel.merge(grav[["iso3_o", "iso3_d", "dist", "tzdiff", "comlang_off", "contig"]],
                        on=["iso3_o", "iso3_d"], how="left")

    panel["pair"] = panel.iso3_o + "-" + panel.iso3_d
    panel["ln_collab"] = np.log1p(panel.collaborators)
    panel["remote_ij"] = (panel.remote_o + panel.remote_d) / 2
    panel["remote_x_dist_z"] = panel.remote_ij * panel.dist_z
    panel["remote_x_cult"] = panel.remote_ij * panel.cult_z
    panel["remote_x_inst"] = panel.remote_ij * panel.inst_z
    panel.to_csv("data/processed/panel_eu_year.csv", index=False)
    print("EU panel:", panel.shape, "pairs:", panel.pair.nunique(),
          "years:", sorted(panel.year.unique()))
    return panel


def run(panel):
    specs = [
        "ln_collab ~ remote_o + remote_d",
        "ln_collab ~ remote_o + remote_d + remote_x_dist_z",
        "ln_collab ~ remote_o + remote_d + remote_x_dist_z + " + " + ".join(CONTROLS),
        "ln_collab ~ remote_o + remote_d + remote_x_cult + " + " + ".join(CONTROLS),
        "ln_collab ~ remote_o + remote_d + remote_x_inst + " + " + ".join(CONTROLS),
    ]
    fits = [pf.feols(f + " | pair + year", data=panel, vcov={"CRV1": "pair"}) for f in specs]
    os.makedirs("output/tables", exist_ok=True)
    pf.etable(fits, type="df").to_csv("output/tables/tab4_eu_ols.csv")
    print("OLS:")
    print(pf.etable(fits, type="df").to_string())

    pfit = []
    for rhs in ["collaborators ~ remote_o + remote_d + remote_x_dist_z",
                "collaborators ~ remote_o + remote_d + remote_x_dist_z + " + " + ".join(CONTROLS)]:
        pfit.append(pf.fepois(rhs + " | pair + year", data=panel, vcov={"CRV1": "pair"}))
    print("PPML:")
    print(pf.etable(pfit, type="df").to_string())
    pf.etable(pfit, type="df").to_csv("output/tables/tab5_eu_ppml.csv")
    return fits, pfit


if __name__ == "__main__":
    panel = build_eu_panel()
    run(panel)
