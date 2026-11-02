"""Download World Bank WGI (governance estimates) and WDI (GDP, internet) via JSON API."""
import requests
import pandas as pd
import time

BASE = "https://api.worldbank.org/v2/country/all/indicator/{code}?date=2015:2024&format=json&per_page=20000&page={page}"


def fetch(code: str) -> pd.DataFrame:
    page = 1
    rows = []
    while True:
        url = BASE.format(code=code, page=page)
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=120)
                data = r.json()
                break
            except Exception as e:
                print(f"retry {code} p{page}: {e}")
                time.sleep(3)
        else:
            raise RuntimeError(f"failed {code} page {page}")
        payload = data[1] if len(data) > 1 and data[1] else []
        rows.extend(payload)
        total = data[0].get("pages", 1) if isinstance(data[0], dict) else data[0][0]["pages"]
        if page >= total:
            break
        page += 1
    df = pd.DataFrame([{
        "country_name": d["country"]["value"], "iso3": d["countryiso3code"],
        "year": int(d["date"]), "value": d["value"]} for d in rows])
    return df


INDICATORS = {
    "NY.GDP.MKTP.KD": "gdp_const2015usd",
    "NY.GDP.PCAP.KD": "gdppc_const2015usd",
    "IT.NET.BBND.P2": "broadband_per100",
    "SP.POP.TOTL": "population",
}

if __name__ == "__main__":
    out = []
    for code, name in INDICATORS.items():
        df = fetch(code)
        df = df[df["iso3"] != ""]
        df = df[["iso3", "year", "value"]].rename(columns={"value": name})
        df["year"] = df["year"].astype(int)
        out.append(df.set_index(["iso3", "year"]))
        print(f"{code}: {name}, rows={len(df)}")
    panel = pd.concat(out, axis=1).reset_index()
    panel.to_csv("data/raw/worldbank_wgi_wdi.csv", index=False)
    print("saved data/raw/worldbank_wgi_wdi.csv", panel.shape)
