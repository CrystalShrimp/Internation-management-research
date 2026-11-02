"""Parse EWCTS 2021 (UKDS SN 9026) into country-level telework indices.

telework (Eurofound-constructed, excludes self-employed):
  1 Employer's premises (no teleworkable)
  2 Employer's premises (some teleworkability)
  3 partial telework (hybrid)
  4 occasional telework
  5 other
  6 full time telework
(NaN = self-employed / not in scope)

Outputs data/processed/ewcs_telework.csv:
  iso2, country, n, telework_any_pct, telework_regular_pct (weighted, weight_core)
"""
from pathlib import Path
import pandas as pd
import numpy as np

DTA = Path("data/raw/ewcs/UKDA-9026-stata/stata/stata13/ewcts_2021_isco2_nace2_nuts2.dta")

# numeric Country code -> (iso2, iso3)
COUNTRY = {
    1: ("AT", "AUT"), 2: ("BE", "BEL"), 3: ("BG", "BGR"), 4: ("CY", "CYP"),
    5: ("CZ", "CZE"), 6: ("DE", "DEU"), 7: ("DK", "DNK"), 8: ("EE", "EST"),
    9: ("EL", "GRC"), 10: ("ES", "ESP"), 11: ("FI", "FIN"), 12: ("FR", "FRA"),
    13: ("HR", "HRV"), 14: ("HU", "HUN"), 15: ("IE", "IRL"), 16: ("IT", "ITA"),
    17: ("LT", "LTU"), 18: ("LU", "LUX"), 19: ("LV", "LVA"), 20: ("MT", "MLT"),
    21: ("NL", "NLD"), 22: ("PL", "POL"), 23: ("PT", "PRT"), 24: ("RO", "ROU"),
    25: ("SE", "SWE"), 26: ("SI", "SVN"), 27: ("SK", "SVK"), 28: ("UK", "GBR"),
    29: ("ME", "MNE"), 30: ("MK", "MKD"), 31: ("RS", "SRB"), 33: ("CH", "CHE"),
    34: ("NO", "NOR"), 35: ("AL", "ALB"), 36: ("BA", "BIH"), 37: ("XK", "XKX"),
}


def build():
    raw = pd.read_stata(DTA, convert_categoricals=False)
    df = raw[["Country", "telework", "weight_core"]].dropna(subset=["Country"])
    df = df[df.weight_core > 0]
    df["iso2"] = df.Country.astype(int).map(lambda k: COUNTRY.get(k, (None, None))[0])
    df["iso3"] = df.Country.astype(int).map(lambda k: COUNTRY.get(k, (None, None))[1])
    df["tw"] = pd.to_numeric(df.telework, errors="coerce")
    df["valid"] = df.tw.notna() & df.tw.between(1, 6)
    df["any"] = df.valid & df.tw.isin([3, 4, 6])           # hybrid + occasional + full
    df["regular"] = df.valid & df.tw.isin([3, 6])          # hybrid + full

    def wstat(g, col):
        v = g[g.valid]
        if not len(v):
            return np.nan
        return 100 * np.average(v[col], weights=v.weight_core)

    name_map = dict(zip(df.Country.astype(int), df.iso2))
    rows = []
    for (iso2, iso3), g in df.groupby(["iso2", "iso3"]):
        rows.append({
            "iso2": iso2, "iso3": iso3,
            "n": int(g.valid.sum()),
            "telework_any_pct": wstat(g, "any"),
            "telework_regular_pct": wstat(g, "regular"),
        })
    out = pd.DataFrame(rows).sort_values("telework_any_pct", ascending=False)
    out.to_csv("data/processed/ewcs_telework.csv", index=False)
    print(out.round(1).to_string(index=False))
    print("saved data/processed/ewcs_telework.csv", out.shape)
    return out


if __name__ == "__main__":
    build()
