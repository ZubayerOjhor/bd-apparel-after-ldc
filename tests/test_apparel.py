"""Tests that run offline: the JSON-stat parser, the scenario maths, and the published dashboard data."""

import json

import pandas as pd
import pytest

from apparel import fetch, scenarios
from apparel.config import DASHBOARD_DATA, GROUP_OF, HS4


def test_every_hs4_line_is_in_exactly_one_group():
    assert len(HS4) == 34 and len(set(HS4)) == 34
    assert set(GROUP_OF) == set(HS4)
    assert all(h[:2] in ("61", "62") for h in HS4)


def test_jsonstat_flattening_puts_values_in_the_right_cells():
    d = {"id": ["partner", "product", "time"], "size": [2, 2, 1],
         "dimension": {"partner": {"category": {"index": {"BD": 0, "VN": 1}}},
                       "product": {"category": {"index": {"6109": 0, "6203": 1}}},
                       "time": {"category": {"index": {"2025": 0}}}},
         "value": {"0": 10, "1": 20, "3": 40}}
    df = fetch._jsonstat(d).set_index(["partner", "product"]).value
    assert df[("BD", "6109")] == 10 and df[("BD", "6203")] == 20 and df[("VN", "6203")] == 40
    assert ("VN", "6109") not in df.index  # empty cells stay empty, not zero


def test_share_loss_formula():
    # A 12% duty with sigma 2 loses 1 - 1.12**-2 = about 20.3% of sales; zero duty loses nothing
    lost = lambda t, s: 1 - (1 + t) ** -s  # noqa: E731
    assert lost(0.12, 2) == pytest.approx(0.2028, abs=1e-4)
    assert lost(0.0, 4) == 0
    assert lost(0.12, 4) > lost(0.12, 2)


def test_gsp_plus_hits_woven_harder_than_knit():
    assert scenarios.NOT_ORIGIN["Woven"] > scenarios.NOT_ORIGIN["Knit"]


@pytest.fixture(scope="module")
def data():
    path = DASHBOARD_DATA / "apparel.json"
    if not path.exists():
        pytest.skip("run `python -m apparel export` first")
    return json.loads(path.read_text("utf8"))


def test_shares_are_fractions_and_markets_complete(data):
    s = pd.DataFrame(data["share_market"])
    assert s.share.between(0, 1).all()
    assert set(s.market) == set(data["meta"]["markets"])
    assert s.groupby(["market", "year"]).share.sum().max() < 1  # five exporters never exceed the world


def test_scenarios_add_up(data):
    g = pd.DataFrame(data["scenario_groups"])
    t = pd.DataFrame(data["scenario_totals"]).set_index("scenario")
    for s in ("kept", "gsp_plus", "lost"):
        assert g[g.scenario == s].duty_eur.sum() == pytest.approx(t.loc[s, "duty_eur"], rel=1e-9)
    assert t.loc["kept", "duty_eur"] == 0
    assert t.loc["kept", "duty_eur"] < t.loc["gsp_plus", "duty_eur"] < t.loc["lost", "duty_eur"]
    assert 0.10 < t.loc["lost", "duty_eur"] / t.loc["lost", "value_eur"] < 0.13  # EU apparel MFN is about 12%


def test_headline_matches_the_detail(data):
    h = data["headline"]
    s = pd.DataFrame(data["share_market"])
    bd25 = s[(s.market == "EU") & (s.exporter == "BD") & (s.year == 2025)].share.iloc[0]
    assert h["eu_share_2025"] == pytest.approx(bd25, rel=1e-4)
    y = {r["exporter"]: r for r in data["eu_ytd"]}
    assert h["eu_ytd_change_bd"] == pytest.approx(y["BD"]["this_year"] / y["BD"]["last_year"] - 1, rel=1e-4)
