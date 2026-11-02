"""Parse G-SWA microdata (user-registered download) into country x wave aggregates.

STEP 1 (discovery): run this as-is with files in data/raw/remote_work/wfh_w1w2_micro_gswa/ -- it prints
the schema of every file so the variable mapping below can be finalised.
STEP 2: fill VARIABLE_MAP with the real column names, then rerun to produce
data/processed/gswa_micro_country_wave.csv
   (iso3, wave, fielded, wfh_actual, wfh_employer_plan, wfh_worker_desire, n)
"""
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np

MICRO_DIR = Path("data/raw/remote_work/wfh_w1w2_micro_gswa")
OUT = Path("data/processed/gswa_micro_country_wave.csv")

NAME_TO_ISO3 = {
    "australia": "AUS", "austria": "AUT", "brazil": "BRA", "canada": "CAN",
    "china": "CHN", "egypt": "EGY", "france": "FRA", "germany": "DEU",
    "greece": "GRC", "hungary": "HUN", "india": "IND", "italy": "ITA",
    "japan": "JPN", "south korea": "KOR", "korea": "KOR", "republic of korea": "KOR",
    "malaysia": "MYS", "netherlands": "NLD", "poland": "POL", "russia": "RUS",
    "serbia": "SRB", "singapore": "SGP", "spain": "ESP", "sweden": "SWE",
    "taiwan": "TWN", "turkey": "TUR", "uk": "GBR", "united kingdom": "GBR",
    "ukraine": "UKR", "usa": "USA", "united states": "USA", "us": "USA",
    "argentina": "ARG", "belgium": "BEL", "bulgaria": "BGR", "croatia": "HRV",
    "cyprus": "CYP", "czechia": "CZE", "czech republic": "CZE", "denmark": "DNK",
    "estonia": "EST", "finland": "FIN", "georgia": "GEO", "iceland": "ISL",
    "ireland": "IRL", "israel": "ISR", "jamaica": "JAM", "kazakhstan": "KAZ",
    "latvia": "LVA", "lithuania": "LTU", "luxembourg": "LUX", "malta": "MLT",
    "mexico": "MEX", "new zealand": "NZL", "nigeria": "NGA", "norway": "NOR",
    "portugal": "PRT", "romania": "ROU", "saudi arabia": "SAU", "slovakia": "SVK",
    "slovenia": "SVN", "south africa": "ZAF", "switzerland": "CHE",
    "united arab emirates": "ARE", "vietnam": "VNM", "philippines": "PHL",
    "thailand": "THA", "indonesia": "IDN", "colombia": "COL", "chile": "CHL",
    "peru": "PER", "morocco": "MAR", "kenya": "KEN", "pakistan": "PAK",
    "bangladesh": "BGD", "hong kong": "HKG", "greece": "GRC",
}

# --- mapping verified against ReadMe.txt of the official replication file ---
VARIABLE_MAP = {
    "country": "original_country",
    "wave": "wave",                        # 1 = Jul/Aug 2021, 2 = Jan/Feb 2022
    "wfh_actual": "n_work_home",           # days worked from home last week
    "wfh_employer_plan": "daysemployer_work_home",
    "wfh_worker_desire": "daysemployee_work_home",
    "weight": None,                        # no sampling weights provided
}


def load_any(path: Path) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf == ".zip":
        zf = zipfile.ZipFile(path)
        inner = [n for n in zf.namelist()
                 if n.lower().endswith((".dta", ".csv")) and "__macosx" not in n.lower()]
        print(f"  zip contains: {zf.namelist()[:10]}")
        name = inner[0]
        inner_path = Path(name)
        if inner_path.suffix.lower() == ".dta":
            return pd.read_stata(zf.open(name))
        return pd.read_csv(zf.open(name))
    if suf == ".dta":
        return pd.read_stata(path)
    if suf in (".csv", ".txt"):
        return pd.read_csv(path)
    if suf in (".sav", ".por"):
        try:
            import pyreadstat
            return pyreadstat.read_sav(path)[0]
        except ImportError:
            raise SystemExit("pip install pyreadstat for SPSS files")
    if suf in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"unknown format {path}")


def discover():
    files = sorted(p for p in MICRO_DIR.rglob("*") if p.suffix.lower()
                   in (".dta", ".csv", ".sav", ".zip", ".xlsx", ".xls"))
    print(f"found {len(files)} candidate files under {MICRO_DIR}")
    frames = {}
    for f in files:
        print("=" * 70)
        print(f.name)
        try:
            df = load_any(f)
            frames[f] = df
            print(f"shape: {df.shape}")
            print("columns:", list(df.columns)[:60])
        except Exception as e:
            print("load failed:", e)
    return frames


def build(frames):
    rows = []
    seen = set()
    for f, df in frames.items():
        needed = {v for v in VARIABLE_MAP.values() if v} - {"wave"}
        if not needed <= set(df.columns):
            print(f"  skip {f}: not a microdata file (missing mapped columns)")
            continue
        sig = (df.shape, tuple(df.columns[:8]))
        if sig in seen:  # .dta and .xlsx of the same data
            print(f"  skip {f}: duplicate of an already-loaded frame")
            continue
        seen.add(sig)
        c_country = VARIABLE_MAP["country"]
        c_wave = VARIABLE_MAP["wave"]
        if c_country is None:
            raise SystemExit("Fill VARIABLE_MAP first (run discovery).")
        vals = {}
        for key in ["wfh_actual", "wfh_employer_plan", "wfh_worker_desire", "weight"]:
            col = VARIABLE_MAP[key]
            vals[key] = pd.to_numeric(df[col], errors="coerce") if col else np.nan
        country_norm = df[c_country].astype(str).str.lower().str.strip()
        iso3 = country_norm.map(NAME_TO_ISO3)
        wt = vals["weight"]
        if isinstance(wt, pd.Series):
            w = wt if wt.notna().any() else pd.Series(1.0, index=df.index)
        else:
            w = pd.Series(1.0, index=df.index)
        tmp = pd.DataFrame({
            "iso3": iso3, "wave": df[c_wave],
            "wfh_actual": vals["wfh_actual"], "wfh_employer_plan": vals["wfh_employer_plan"],
            "wfh_worker_desire": vals["wfh_worker_desire"], "w": w})
        tmp = tmp.dropna(subset=["iso3", "wfh_actual"])
        def wmean(g, c):
            x, ww = g[c], g["w"]
            m = x.notna()
            return np.average(x[m], weights=ww[m]) if m.any() else np.nan
        agg = tmp.groupby(["iso3", "wave"]).apply(
            lambda g: pd.Series({
                "wfh_actual": wmean(g, "wfh_actual"),
                "wfh_employer_plan": wmean(g, "wfh_employer_plan"),
                "wfh_worker_desire": wmean(g, "wfh_worker_desire"),
                "n": len(g)})).reset_index()
        rows.append(agg)
    out = pd.concat(rows)
    out.to_csv(OUT, index=False)
    print(out.groupby("wave")[["iso3"]].count())
    print("saved", OUT)
    return out


if __name__ == "__main__":
    frames = discover()
    if all(VARIABLE_MAP[k] for k in ["country", "wave", "wfh_actual"]):
        build(frames)
    else:
        print("\nVARIABLE_MAP incomplete -- fill in column names from the schema above.")
