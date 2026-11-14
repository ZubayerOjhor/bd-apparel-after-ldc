"""Write dashboard/data/apparel.json: everything the dashboard and the memo charts read."""

import json
from datetime import datetime, timezone

import duckdb
import pandas as pd

from . import scenarios
from .config import DASHBOARD_DATA, EXPORTERS, MARKETS, PRODUCT_GROUPS, REF


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", double_precision=5))


def build(con: duckdb.DuckDBPyConnection) -> dict:
    q = lambda s: con.execute(s).df()  # noqa: E731
    share_market = q("select market, exporter, year, value_usd, share from share_market order by 1, 2, 3")
    share_group = q('select market, "group", exporter, year, value_usd, world_usd, share from share_group order by 1, 2, 3, 4')
    unit = q('select market, "group", exporter, year, usd_per_item, eur_per_kg from unit_value order by 1, 2, 3, 4')
    ytd_month = q("select max(month) from eu_monthly where exporter = 'BD'").iloc[0, 0]
    m = int(ytd_month[5:])
    ytd = q(f"""select exporter,
                       sum(value_eur) filter (where month between '2026-01' and '{ytd_month}') as this_year,
                       sum(value_eur) filter (where month between '2025-01' and '2025-{m:02d}') as last_year
                from eu_monthly group by 1""")
    ytd["change"] = ytd.this_year / ytd.last_year - 1
    world = ytd.set_index("exporter").loc["WORLD"]
    ytd["share_this_year"] = ytd.this_year / world.this_year
    ytd["share_last_year"] = ytd.last_year / world.last_year
    monthly = q("select exporter, month, sum(value_eur) as value_eur from eu_monthly group by all order by 1, 2")

    by_group = scenarios.by_group(con)
    totals = scenarios.totals(con)
    regimes = pd.read_csv(REF / "eu_regimes.csv")
    exposure = q('select hs4, "group", fabric, value_eur, mfn, duty_eur_if_mfn from exposure_eu order by value_eur desc')

    def pick(market, exporter, year):
        r = share_market[(share_market.market == market) & (share_market.exporter == exporter) & (share_market.year == year)]
        return float(r.share.iloc[0])

    lost = totals.set_index("scenario").loc["lost"]
    gsp = totals.set_index("scenario").loc["gsp_plus"]
    headline = {
        "eu_share_2015": pick("EU", "BD", 2015), "eu_share_2022": pick("EU", "BD", 2022), "eu_share_2025": pick("EU", "BD", 2025),
        "eu_cn_2022": pick("EU", "CN", 2022), "eu_cn_2025": pick("EU", "CN", 2025),
        "us_share_2015": pick("US", "BD", 2015), "us_share_2025": pick("US", "BD", 2025),
        "us_cn_2015": pick("US", "CN", 2015), "us_cn_2025": pick("US", "CN", 2025),
        "us_vn_2015": pick("US", "VN", 2015), "us_vn_2025": pick("US", "VN", 2025),
        "uk_share_2019": pick("UK", "BD", 2019), "uk_share_2025": pick("UK", "BD", 2025),
        "eu_ytd_month": ytd_month,
        "eu_ytd_change_bd": float(ytd.set_index("exporter").loc["BD", "change"]),
        "eu_ytd_change_cn": float(ytd.set_index("exporter").loc["CN", "change"]),
        "eu_ytd_change_vn": float(ytd.set_index("exporter").loc["VN", "change"]),
        "eu_ytd_change_world": float(world.this_year / world.last_year - 1),
        "eu_bd_value_2025_eur": float(lost.value_eur),
        "duty_lost_eur": float(lost.duty_eur), "duty_gsp_eur": float(gsp.duty_eur),
        "risk_lost_low": float(lost.exports_at_risk_low), "risk_lost_high": float(lost.exports_at_risk_high),
        "risk_gsp_low": float(gsp.exports_at_risk_low), "risk_gsp_high": float(gsp.exports_at_risk_high),
    }
    return {
        "meta": {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                 "years": [int(share_market.year.min()), int(share_market.year.max())],
                 "exporters": {k: v["name"] for k, v in EXPORTERS.items()},
                 "markets": {k: v["name"] for k, v in MARKETS.items()},
                 "groups": list(PRODUCT_GROUPS),
                 "sigma": list(scenarios.SIGMA), "not_origin": scenarios.NOT_ORIGIN,
                 "scenarios": scenarios.SCENARIOS},
        "headline": headline,
        "share_market": _records(share_market),
        "share_group": _records(share_group),
        "unit_value": _records(unit),
        "eu_ytd": _records(ytd),
        "eu_monthly": _records(monthly),
        "scenario_groups": _records(by_group),
        "scenario_totals": _records(totals),
        "exposure": _records(exposure),
        "regimes": _records(regimes),
    }


def write(con: duckdb.DuckDBPyConnection) -> dict:
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    d = build(con)
    (DASHBOARD_DATA / "apparel.json").write_text(json.dumps(d, separators=(",", ":")), "utf8")
    return d
