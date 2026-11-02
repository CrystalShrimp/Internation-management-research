"""Parse WGI (6 governance estimates, latest <=2022), Hofstede (6 cultural dims), Eurostat WFH, CEPII bilateral gravity variables."""
import zipfile
import pandas as pd
import numpy as np
import openpyxl
import json

# WGI code quirks (legacy codes)
WGI_CODE_FIX = {"ADO": "AND", "ZAR": "COD", "ROM": "ROU", "TMP": "TLS", "KSV": "XKX", "WBG": "PSE"}


def parse_wgi():
    wb = openpyxl.load_workbook("data/raw/wgi_dataset.xlsx", read_only=True, data_only=True)
    sheets = {
        "VoiceandAccountability": "wgi_va", "Political StabilityNoViolence": "wgi_pv",
        "GovernmentEffectiveness": "wgi_ge", "RegulatoryQuality": "wgi_rq",
        "RuleofLaw": "wgi_rl", "ControlofCorruption": "wgi_cc",
    }
    out = {}
    for sheet, col in sheets.items():
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        years = rows[13]
        subcols = rows[14]
        # column offsets of 'Estimate' subcolumns and their years
        est_cols = [(j, int(years[j])) for j in range(len(years))
                    if years[j] is not None and subcols[j] == "Estimate"]
        latest = max(y for _, y in est_cols)
        use_cols = {y: j for j, y in est_cols if y >= latest - 2}  # 2021 or 2022
        for r in rows[15:]:
            if r[1] is None:
                continue
            code = WGI_CODE_FIX.get(r[1], r[1])
            name = r[0]
            if not isinstance(name, str) or len(code) != 3:
                continue
            # prefer latest year with data
            for y in sorted(use_cols, reverse=True):
                v = r[use_cols[y]]
                if isinstance(v, (int, float)):
                    out.setdefault(code, {"iso3": code, "country": name})[col] = float(v)
                    out[code]["wgi_year"] = y
                    break
    df = pd.DataFrame(out.values())
    df.to_csv("data/raw/wgi_clean.csv", index=False)
    print("WGI:", df.shape, "latest year:", df.wgi_year.unique())
    return df


HOFSTEDE_NAME_TO_ISO3 = {
    "albania": "ALB", "algeria": "DZA", "argentina": "ARG", "armenia": "ARM",
    "australia": "AUS", "austria": "AUT", "azerbaijan": "AZE", "bangladesh": "BGD",
    "belarus": "BLR", "belgium": "BEL", "bolivia": "BOL", "bosnia and herzegovina": "BIH",
    "brazil": "BRA", "bulgaria": "BGR", "burkina faso": "BFA", "cambodia": "KHM",
    "cameroon": "CMR", "canada": "CAN", "chile": "CHL", "china": "CHN",
    "colombia": "COL", "costa rica": "CRI", "croatia": "HRV", "czech republic": "CZE",
    "czechia": "CZE", "denmark": "DNK", "ecuador": "ECU", "egypt": "EGY",
    "el salvador": "SLV", "estonia": "EST", "ethiopia": "ETH", "finland": "FIN",
    "france": "FRA", "georgia": "GEO", "germany": "DEU", "greece": "GRC",
    "guatemala": "GTM", "hong kong": "HKG", "hong kong sar": "HKG", "honduras": "HND",
    "hungary": "HUN", "iceland": "ISL", "india": "IND", "indonesia": "IDN",
    "iran": "IRN", "iraq": "IRQ", "ireland": "IRL", "israel": "ISR",
    "italy": "ITA", "jamaica": "JAM", "japan": "JPN", "jordan": "JOR",
    "kazakhstan": "KAZ", "kenya": "KEN", "korea south": "KOR", "south korea": "KOR",
    "kuwait": "KWT", "kyrgyzstan": "KGZ", "latvia": "LVA", "lebanon": "LBN",
    "libya": "LBY", "lithuania": "LTU", "luxembourg": "LUX", "malaysia": "MYS",
    "malta": "MLT", "mauritius": "MUS", "mexico": "MEX", "moldova": "MDA",
    "morocco": "MAR", "mozambique": "MOZ", "myanmar": "MMR", "nepal": "NPL",
    "netherlands": "NLD", "new zealand": "NZL", "nigeria": "NGA", "norway": "NOR",
    "oman": "OMN", "pakistan": "PAK", "panama": "PAN", "paraguay": "PRY",
    "peru": "PER", "philippines": "PHL", "poland": "POL", "portugal": "PRT",
    "qatar": "QAT", "romania": "ROU", "russia": "RUS", "rwanda": "RWA",
    "saudi arabia": "SAU", "senegal": "SEN", "serbia": "SRB", "singapore": "SGP",
    "slovakia": "SVK", "slovenia": "SVN", "south africa": "ZAF", "spain": "ESP",
    "sudan": "SDN", "sweden": "SWE", "switzerland": "CHE", "syria": "SYR",
    "taiwan": "TWN", "tanzania": "TZA", "thailand": "THA", "trinidad and tobago": "TTO",
    "tunisia": "TUN", "turkey": "TUR", "uganda": "UGA", "ukraine": "UKR",
    "united arab emirates": "ARE", "united kingdom": "GBR", "great britain": "GBR", "u.s.a.": "USA", "united states": "USA",
    "uruguay": "URY", "uzbekistan": "UZB", "venezuela": "VEN", "vietnam": "VNM",
    "zambia": "ZMB", "zimbabwe": "ZWE", "china hong kong": "HKG",
}


def parse_hofstede():
    df = pd.read_csv("data/raw/hofstede_6d.csv", sep=";")
    dims = ["pdi", "idv", "mas", "uai", "ltowvs", "ivr"]
    rows = []
    for _, r in df.iterrows():
        iso3 = HOFSTEDE_NAME_TO_ISO3.get(str(r["country"]).lower().strip())
        if iso3 is None:
            continue
        vals = {}
        for d in dims:
            v = r[d]
            try:
                vals[d] = float(v) if "#NULL" not in str(v) else np.nan
            except (ValueError, TypeError):
                vals[d] = np.nan
        vals["iso3"] = iso3
        vals["country"] = r["country"]
        rows.append(vals)
    hof = pd.DataFrame(rows)
    hof.to_csv("data/raw/hofstede_clean.csv", index=False)
    print("Hofstede:", hof.shape, "complete 6-dim:", hof[dims].notna().all(axis=1).sum())
    return hof


def parse_eurostat():
    d = json.load(open("data/raw/eurostat_ehomp.json", encoding="utf-8"))
    dims = d["dimension"]
    def idx_labels(dim):
        v = dims[dim]["category"]
        return {i: code for code, i in v["index"].items()}
    sizes = {k: len(dims[k]["category"]["index"]) for k in dims}
    order = list(dims.keys())
    # value key = concatenated indices in dimension order
    def decode(key):
        k = int(key)
        coord = []
        for dim in reversed(order):
            coord.append(k % sizes[dim])
            k //= sizes[dim]
        coord = list(reversed(coord))
        return {dim: idx_labels(dim)[coord[i]] for i, dim in enumerate(order)}
    rows = []
    for key, val in d["value"].items():
        c = decode(key)
        if (c.get("sex") == "T" and c.get("age") == "Y20-64" and c.get("wstatus") == "SAL"
                and c.get("unit") == "PC" and c.get("frequenc") in ("USU", "SMT")):
            rows.append({
                "geo": c["geo"], "year": int(c["time"]),
                "freq_wfh": c["frequenc"], "pct": val,
            })
    df = pd.DataFrame(rows)
    piv = df.pivot_table(index=["geo", "year"], columns="freq_wfh", values="pct").reset_index()
    piv = piv.rename(columns={"USU": "wfh_usually_pct", "SMT": "wfh_sometimes_pct"})
    if "wfh_usually_pct" not in piv.columns:
        piv["wfh_usually_pct"] = np.nan
    if "wfh_sometimes_pct" not in piv.columns:
        piv["wfh_sometimes_pct"] = np.nan
    piv["wfh_ever_pct"] = piv["wfh_usually_pct"].fillna(0) + piv["wfh_sometimes_pct"].fillna(0)
    piv.to_csv("data/raw/eurostat_wfh_clean.csv", index=False)
    print("Eurostat WFH:", piv.shape, "geo:", piv.geo.nunique())
    return piv


def parse_cepii():
    z = zipfile.ZipFile("data/raw/gravity_cepii.zip")
    rows = []
    for chunk in pd.read_csv(z.open("Gravity_V202211.csv"), chunksize=500000, low_memory=False):
        c = chunk[chunk["year"].isin([2019, 2020, 2021])]
        if len(c):
            rows.append(c[["year", "iso3_o", "iso3_d", "dist", "distw_harmonic", "distcap",
                           "contig", "comlang_off", "comlang_ethno", "comcol", "col_dep",
                           "sibling", "gmt_offset_2020_o", "gmt_offset_2020_d", "scaled_sci_2021"]])
    df = pd.concat(rows).sort_values("year")
    # static bilateral variables: take first non-missing across years per pair
    df = df.groupby(["iso3_o", "iso3_d"], as_index=False).first()
    df["tzdiff"] = (df["gmt_offset_2020_o"] - df["gmt_offset_2020_d"]).abs()
    keep = ["iso3_o", "iso3_d", "dist", "distw_harmonic", "distcap", "contig",
            "comlang_off", "comlang_ethno", "comcol", "col_dep", "sibling", "tzdiff",
            "scaled_sci_2021"]
    df = df[keep].drop_duplicates(subset=["iso3_o", "iso3_d"])
    df.to_csv("data/raw/cepii_bilateral.csv", index=False)
    print("CEPII bilateral:", df.shape,
          "missing dist:", df.dist.isna().sum())
    return df


if __name__ == "__main__":
    parse_wgi()
    parse_hofstede()
    parse_eurostat()
    parse_cepii()
