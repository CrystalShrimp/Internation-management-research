"""Parse G-SWA wave tables: W1+W2 pooled (NBER w30446 Table A.2) and W3 (GSWA-Figures-Data-2023.xlsx)."""
import pandas as pd
import pdfplumber
import openpyxl

NAME_TO_ISO3 = {
    "australia": "AUS", "austria": "AUT", "brazil": "BRA", "canada": "CAN",
    "china": "CHN", "egypt": "EGY", "france": "FRA", "germany": "DEU",
    "greece": "GRC", "hungary": "HUN", "india": "IND", "italy": "ITA",
    "japan": "JPN", "s. korea": "KOR", "south korea": "KOR", "malaysia": "MYS",
    "netherlands": "NLD", "poland": "POL", "russia": "RUS", "serbia": "SRB",
    "singapore": "SGP", "spain": "ESP", "sweden": "SWE", "taiwan": "TWN",
    "turkey": "TUR", "uk": "GBR", "united kingdom": "GBR", "ukraine": "UKR",
    "usa": "USA", "united states": "USA", "united states of america": "USA",
    "argentina": "ARG", "belgium": "BEL", "bulgaria": "BGR", "croatia": "HRV",
    "cyprus": "CYP", "czech republic": "CZE", "czechia": "CZE", "denmark": "DNK",
    "estonia": "EST", "finland": "FIN", "georgia": "GEO", "iceland": "ISL",
    "ireland": "IRL", "israel": "ISR", "jamaica": "JAM", "kazakhstan": "KAZ",
    "latvia": "LVA", "lithuania": "LTU", "luxembourg": "LUX", "malta": "MLT",
    "mexico": "MEX", "new zealand": "NZL", "nigeria": "NGA", "norway": "NOR",
    "portugal": "PRT", "romania": "ROU", "saudi arabia": "SAU", "slovakia": "SVK",
    "slovenia": "SVN", "south africa": "ZAF", "switzerland": "CHE",
    "united arab emirates": "ARE", "vietnam": "VNM", "philippines": "PHL",
    "thailand": "THA", "indonesia": "IDN", "colombia": "COL", "chile": "CHL",
    "peru": "PER", "morocco": "MAR", "kenya": "KEN", "pakistan": "PAK",
    "bangladesh": "BGD", "hong kong": "HKG", "hong kong sar": "HKG",
}


def parse_w12():
    """NBER w30446 Table A.2: pooled W1 (mid-2021) + W2 (early 2022) raw means."""
    rows = []
    with pdfplumber.open("data/raw/archive/nber_w30446.pdf") as pdf:
        text = pdf.pages[57].extract_text()
    for line in text.split("\n"):
        parts = line.split()
        if len(parts) >= 8:
            name_parts = parts[:-8]
            name = " ".join(name_parts)
            tail = parts[-8:]
            try:
                vals = [float(x) for x in tail]
            except ValueError:
                continue
            iso3 = NAME_TO_ISO3.get(name.lower().strip())
            if iso3 and len(vals) == 8:
                # age, actual, employer plans, worker desires, productivity surprise,
                # commute, wtp, social acceptance  (8 numeric cols)
                rows.append({
                    "country": name, "iso3": iso3, "wave": "W1W2",
                    "wfh_actual": vals[1], "wfh_employer_plan": vals[2],
                    "wfh_worker_desire": vals[3],
                })
    df = pd.DataFrame(rows)
    df.to_csv("data/raw/archive/wfh_w1w2_nber_table.csv", index=False)
    print(f"W1W2: {len(df)} countries")
    return df


def parse_w3():
    """GSWA-Figures-Data-2023.xlsx: Wave 3 fielded April-May 2023."""
    wb = openpyxl.load_workbook("data/raw/remote_work/wfh_w3_summary_gswa.xlsx", read_only=True, data_only=True)
    out = {}
    for sheet, col in [("Figure 1", "wfh_actual"), ("Figure 4", "wfh_employer_plan"),
                       ("Figure 3", "wfh_worker_desire")]:
        ws = wb[sheet]
        for row in ws.iter_rows(min_row=3, values_only=True):
            name, val = row[0], row[1]
            if not name or val is None:
                continue
            iso3 = NAME_TO_ISO3.get(str(name).lower().strip())
            if iso3:
                out.setdefault(iso3, {"country": str(name).strip(), "iso3": iso3})[col] = float(val)
    df = pd.DataFrame(out.values())
    df["wave"] = "W3"
    df.to_csv("data/processed/wfh_w3_gswa.csv", index=False)
    print(f"W3: {len(df)} countries")
    return df


if __name__ == "__main__":
    w12 = parse_w12()
    w3 = parse_w3()
    print(w12.head(3))
    print(w3.head(3))
    common = set(w12.iso3) & set(w3.iso3)
    print("common countries:", len(common))
