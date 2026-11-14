"""Download the public data the study uses, once, into data/raw. Every call is cached, so reruns are offline.

Sources
- Eurostat Comext DS-045409: EU27 (2020 composition) imports by partner and HS4, annual and monthly (value in EUR, net mass).
- UN Comtrade public API: imports of the US, UK, Canada, Japan and Australia by partner and HS4 (value in USD,
  quantity in items). The public endpoint is rate limited, so calls are spaced out and retried.
- WITS / UNCTAD TRAINS: MFN tariff lines (HS6) for the EU and the US.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from .config import EXPORTERS, HS4, MARKETS, RAW, WORLD_M49, YEARS

UA = {"User-Agent": "bd-apparel-after-ldc (research; github.com/ZubayerOjhor)"}
EUROSTAT = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"
COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
WITS = "https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/reporter/{rep}/partner/000/product/all/year/{year}/datatype/reported?format=JSON"


def _get(url: str, tries: int = 6, wait: float = 8.0) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or k == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if k == tries - 1:
                raise
        time.sleep(wait * (k + 1))
    raise RuntimeError(url)


def _cached(path: Path, url: str, pause: float = 0.0) -> dict:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get(url))
        time.sleep(pause)
    return json.loads(path.read_text("utf8"))


def _jsonstat(d: dict) -> pd.DataFrame:
    """Flatten a JSON-stat 2.0 dataset into one row per non-empty cell."""
    ids, size = d["id"], d["size"]
    cats = [sorted(d["dimension"][i]["category"]["index"].items(), key=lambda kv: kv[1]) for i in ids]
    rows = []
    for flat, v in d["value"].items():
        n, coords = int(flat), []
        for s in reversed(size):
            coords.append(n % s)
            n //= s
        coords.reverse()
        rows.append({i: cats[j][coords[j]][0] for j, i in enumerate(ids)} | {"value": v})
    return pd.DataFrame(rows)


def eurostat_annual() -> pd.DataFrame:
    # The extra-EU total comes back empty when it is requested next to single countries, so it is a separate call
    frames = []
    products = "&".join(f"product={h}" for h in HS4)
    for year in YEARS:
        for tag, partners in (("", list(EXPORTERS)), ("_world", ["EXT_EU27_2020"])):
            q = "&".join(f"partner={p}" for p in partners)
            url = f"{EUROSTAT}?format=JSON&freq=A&reporter=EU27_2020&flow=1&{q}&{products}&time={year}"
            frames.append(_jsonstat(_cached(RAW / "eurostat" / f"annual_{year}{tag}.json", url)))
    df = pd.concat(frames)
    df = df.pivot_table(index=["partner", "product", "time"], columns="indicators", values="value", aggfunc="sum").reset_index()
    return df.rename(columns={"partner": "exporter", "product": "hs4", "time": "year",
                              "VALUE_IN_EUROS": "value_eur", "QUANTITY_IN_100KG": "qty_100kg"})


def eurostat_annual_hs2() -> pd.DataFrame:
    """Chapter totals (61, 62). Some trade, mostly from China since 2022, is recorded at chapter level only,
    so market totals come from here and product detail from eurostat_annual()."""
    frames = []
    for year in YEARS:
        for tag, partners in (("", list(EXPORTERS)), ("_world", ["EXT_EU27_2020"])):
            q = "&".join(f"partner={p}" for p in partners)
            url = f"{EUROSTAT}?format=JSON&freq=A&reporter=EU27_2020&flow=1&{q}&product=61&product=62&indicators=VALUE_IN_EUROS&time={year}"
            frames.append(_jsonstat(_cached(RAW / "eurostat" / f"annual_hs2_{year}{tag}.json", url)))
    df = pd.concat(frames)
    return pd.DataFrame({"exporter": df.partner.replace({"EXT_EU27_2020": "WORLD"}), "hs2": df["product"],
                         "year": df.time.astype(int), "value_eur": df.value})


def eurostat_monthly(since: str = "2024-01") -> pd.DataFrame:
    frames = []
    for tag, partners in (("", list(EXPORTERS)), ("_world", ["EXT_EU27_2020"])):
        q = "&".join(f"partner={p}" for p in partners)
        url = f"{EUROSTAT}?format=JSON&freq=M&reporter=EU27_2020&flow=1&{q}&product=61&product=62&indicators=VALUE_IN_EUROS&sinceTimePeriod={since}"
        frames.append(_jsonstat(_cached(RAW / "eurostat" / f"monthly_since_{since}{tag}.json", url)))
    df = pd.concat(frames)
    return df.rename(columns={"partner": "exporter", "product": "hs2", "time": "month", "value": "value_eur"})[
        ["exporter", "hs2", "month", "value_eur"]]


def comtrade(market: str) -> pd.DataFrame:
    rep = MARKETS[market]["m49"]
    partners = ",".join(str(e["m49"]) for e in EXPORTERS.values()) + f",{WORLD_M49}"
    rows = []
    for year in YEARS:
        url = f"{COMTRADE}?reporterCode={rep}&period={year}&partnerCode={partners}&cmdCode={','.join(HS4)}&flowCode=M"
        d = _cached(RAW / "comtrade" / f"{market}_{year}.json", url, pause=6.0)
        if d.get("error"):
            raise RuntimeError(f"Comtrade {market} {year}: {d['error']}")
        rows += d["data"]
    m49 = {e["m49"]: k for k, e in EXPORTERS.items()} | {WORLD_M49: "WORLD"}
    df = pd.DataFrame(rows)
    df = df[(df.customsCode == "C00") & (df.motCode == 0) & (df.partner2Code == 0)]
    return pd.DataFrame({"market": market, "exporter": df.partnerCode.map(m49), "hs4": df.cmdCode, "year": df.refYear,
                         "value_usd": df.primaryValue, "qty": df.qty, "qty_unit": df.qtyUnitCode})


def eur_usd() -> pd.DataFrame:
    """ECB reference rate, annual average, USD per EUR (Eurostat ert_bil_eur_a)."""
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ert_bil_eur_a"
           f"?format=JSON&currency=USD&statinfo=AVG&sinceTimePeriod={YEARS[0]}")
    d = _cached(RAW / "eurostat" / "eur_usd.json", url)
    idx = d["dimension"]["time"]["category"]["index"]
    return pd.DataFrame([{"year": int(y), "usd_per_eur": d["value"][str(i)]} for y, i in idx.items() if str(i) in d["value"]])


def wits_mfn(reporter: str, year: int) -> pd.DataFrame:
    """MFN applied tariff, simple average across the HS6 lines of chapters 61 and 62."""
    code = {"EU": "918", "US": "840"}[reporter]
    d = _cached(RAW / "wits" / f"{reporter}_{year}.json", WITS.format(rep=code, year=year))
    dims = d["structure"]["dimensions"]["series"]
    products = [v["id"] for v in next(x for x in dims if x["id"] == "PRODUCTCODE")["values"]]
    series = d["dataSets"][0]["series"]
    # WITS keys do not follow the declared keyPosition, so find the slot that indexes the products
    keys = [list(map(int, k.split(":"))) for k in series]
    prod = max(range(len(keys[0])), key=lambda i: max(k[i] for k in keys))
    rows = []
    for key, s in series.items():
        hs6 = products[int(key.split(":")[prod])]
        if hs6[:2] in ("61", "62"):
            obs = next(iter(s["observations"].values()))
            rows.append({"market": reporter, "hs6": hs6, "mfn": obs[0]})
    return pd.DataFrame(rows)
