"""Turn the raw downloads into one tidy fact table and the marts the memo and dashboard read from."""

import duckdb
import pandas as pd

from . import fetch
from .config import EXPORTERS, GROUP_OF, MARKETS, WAREHOUSE

TARIFF_YEAR = 2022  # latest year WITS has reported MFN lines for both the EU and the US


def fact_trade() -> pd.DataFrame:
    fx = fetch.eur_usd().set_index("year").usd_per_eur
    eu = fetch.eurostat_annual()
    eu = pd.DataFrame({
        "market": "EU",
        "exporter": eu.exporter.replace({"EXT_EU27_2020": "WORLD"}),
        "hs4": eu.hs4, "year": eu.year.astype(int),
        "value_usd": eu.value_eur * eu.year.astype(int).map(fx),
        "value_local": eu.value_eur,
        "items": pd.NA,
        "kg": eu.qty_100kg * 100,
    })
    frames = [eu]
    for m, spec in MARKETS.items():
        if spec["source"] != "comtrade":
            continue
        c = fetch.comtrade(m)
        frames.append(pd.DataFrame({
            "market": m, "exporter": c.exporter, "hs4": c.hs4, "year": c.year.astype(int),
            "value_usd": c.value_usd, "value_local": c.value_usd,
            # Comtrade unit 5 is "number of items"; anything else is left out of price per item
            "items": c.qty.where(c.qty_unit == 5), "kg": pd.NA,
        }))
    df = pd.concat(frames, ignore_index=True)
    df["group"] = df.hs4.map(GROUP_OF)
    df["fabric"] = df.hs4.str[:2].map({"61": "Knit", "62": "Woven"})
    return df


def mfn() -> pd.DataFrame:
    t = pd.concat([fetch.wits_mfn("EU", TARIFF_YEAR), fetch.wits_mfn("US", TARIFF_YEAR)])
    t["hs4"] = t.hs6.str[:4]
    return t.groupby(["market", "hs4"], as_index=False).mfn.mean()


MARTS = """
create or replace table share_market as
with t as (
    select market, exporter, year, sum(value_usd) v from fact_trade where market <> 'EU' group by all
    union all
    select 'EU', exporter, year, sum(value_usd) from eu_hs2 group by all)
select a.market, a.exporter, a.year, a.v as value_usd, a.v / w.v as share
from t a join t w on w.market = a.market and w.year = a.year and w.exporter = 'WORLD'
where a.exporter <> 'WORLD';

create or replace table share_group as
with t as (select market, "group", exporter, year, sum(value_usd) v from fact_trade group by all)
select a.market, a."group", a.exporter, a.year, a.v as value_usd, w.v as world_usd, a.v / w.v as share
from t a join t w on w.market = a.market and w."group" = a."group" and w.year = a.year and w.exporter = 'WORLD'
where a.exporter <> 'WORLD';

create or replace table unit_value as
select market, "group", exporter, year,
       sum(value_usd) filter (where items > 0) / nullif(sum(items) filter (where items > 0), 0) as usd_per_item,
       sum(value_local) filter (where kg > 0) / nullif(sum(kg) filter (where kg > 0), 0) as eur_per_kg
from fact_trade where exporter <> 'WORLD' group by all;

create or replace table exposure_eu as
select f.hs4, f."group", f.fabric, f.value_usd, f.value_local as value_eur, m.mfn,
       f.value_local * m.mfn / 100 as duty_eur_if_mfn
from fact_trade f join mfn m on m.market = 'EU' and m.hs4 = f.hs4
where f.market = 'EU' and f.exporter = 'BD' and f.year = (select max(year) from fact_trade where market = 'EU');
"""


def _load(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> None:
    con.register("_df", df)
    con.execute(f"create or replace table {name} as select * from _df")
    con.unregister("_df")


def run(quiet: bool = False) -> duckdb.DuckDBPyConnection:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    _load(con, "fact_trade", fact_trade())
    _load(con, "mfn", mfn())
    fx = fetch.eur_usd().set_index("year").usd_per_eur
    h2 = fetch.eurostat_annual_hs2()
    h2["value_usd"] = h2.value_eur * h2.year.map(fx)
    _load(con, "eu_hs2", h2)
    m = fetch.eurostat_monthly()
    m["exporter"] = m.exporter.replace({"EXT_EU27_2020": "WORLD"})
    _load(con, "eu_monthly", m)
    for stmt in filter(str.strip, MARTS.split(";")):
        con.execute(stmt)
    if not quiet:
        n = con.execute("select count(*) from fact_trade").fetchone()[0]
        print(f"fact_trade: {n:,} rows across {len(MARKETS)} markets and {len(EXPORTERS)} exporters")
    return con
