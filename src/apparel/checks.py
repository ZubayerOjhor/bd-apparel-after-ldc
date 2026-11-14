"""Checks that must pass before anything is exported. Each returns (name, ok, detail)."""

from dataclasses import dataclass

import duckdb

from .config import HS4, MARKETS, YEARS


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


def _one(con, sql):
    return con.execute(sql).fetchone()


def run(con: duckdb.DuckDBPyConnection) -> list[Result]:
    out = []

    # 1. Bangladesh is present in every market for every year, so trends are not broken by gaps
    missing = con.execute(f"""
        select m.market, y.year from (select unnest({list(MARKETS)}) as market) m, (select unnest({YEARS}) as year) y
        where not exists (select 1 from fact_trade f where f.market = m.market and f.year = y.year and f.exporter = 'BD')
        """).fetchall()
    out.append(Result("Bangladesh has data in every market and year", not missing, f"{len(missing)} market-years missing: {missing[:6]}"))

    # 2. A market's imports from the world are at least its imports from our five exporters
    n, worst = _one(con, """
        with t as (select market, hs4, year, sum(value_usd) filter (where exporter <> 'WORLD') five,
                          sum(value_usd) filter (where exporter = 'WORLD') world from fact_trade group by all)
        select count(*) filter (where five > world * 1.001), max(five / nullif(world, 0)) from t where world is not null""")
    out.append(Result("World imports cover the five exporters", n == 0, f"{n} cells over, highest ratio {worst:.3f}"))

    # 3. Eurostat agrees with itself: product detail sums to chapter totals, and 12 months sum to the year.
    #    China is excluded on purpose: part of its trade is recorded at chapter level only (reported in check 7).
    gap = _one(con, """
        with d as (select exporter, year, sum(value_local) v from fact_trade where market = 'EU' group by all),
             c as (select exporter, year, sum(value_eur) v from eu_hs2 group by all),
             m as (select exporter, sum(value_eur) v from eu_monthly where month like '2025-%' group by 1)
        select greatest(
            (select max(abs(d.v / c.v - 1)) from d join c using (exporter, year) where exporter not in ('CN', 'WORLD')),
            (select max(abs(m.v / c.v - 1)) from m join c using (exporter) where c.year = 2025))""")[0]
    out.append(Result("EU product detail and months tie to chapter totals", gap < 0.005, f"largest gap {gap:.3%}"))

    # 4. No negative values, shares between 0 and 1
    bad = _one(con, "select count(*) from fact_trade where value_usd < 0")[0] + \
        _one(con, "select count(*) from share_group where share < 0 or share > 1")[0]
    out.append(Result("No negative values, shares within 0 to 1", bad == 0, f"{bad} bad rows"))

    # 5. Unit values in a plausible band, so a unit mix-up shows up here and not in a chart
    lo, hi = _one(con, "select min(usd_per_item), max(usd_per_item) from unit_value where usd_per_item is not null and market = 'US'")
    elo, ehi = _one(con, "select min(eur_per_kg), max(eur_per_kg) from unit_value where eur_per_kg is not null")
    ok = 0.3 <= lo and hi <= 300 and 3 <= elo and ehi <= 300
    out.append(Result("Unit values in a plausible range", ok, f"US ${lo:.2f} to ${hi:.2f} an item, EU EUR {elo:.1f} to {ehi:.1f} a kg"))

    # 6. Every product line has an MFN rate in both tariff schedules, and rates look like apparel rates
    n_eu, n_us, mx = _one(con, "select count(*) filter (where market = 'EU'), count(*) filter (where market = 'US'), max(mfn) from mfn")
    ok = n_eu == len(HS4) and n_us == len(HS4) and 0 <= mx <= 35
    out.append(Result("MFN tariff for all 34 product lines", ok, f"EU {n_eu}, US {n_us}, highest {mx:.1f}%"))

    # 7. Size the EU trade that has no product detail, so product-level shares are read with it in mind
    share, cn = _one(con, """
        with d as (select exporter, sum(value_local) v from fact_trade where market = 'EU' and year = 2025 group by 1),
             c as (select exporter, sum(value_eur) v from eu_hs2 where year = 2025 group by 1)
        select 1 - (select v from d where exporter = 'WORLD') / (select v from c where exporter = 'WORLD'),
               (select c.v - d.v from c join d using (exporter) where exporter = 'CN')""")
    out.append(Result("EU trade without product detail is small", share < 0.06,
                      f"{share:.1%} of 2025 EU imports, of which China EUR {cn / 1e9:.1f}bn"))
    return out
