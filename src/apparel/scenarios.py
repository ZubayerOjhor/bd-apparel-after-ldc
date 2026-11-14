"""EU access scenarios for Bangladesh apparel after Everything But Arms ends (about November 2032).

Every number here is an assumption, written down so a reader can disagree with it.

Duty: the EU MFN rate for each HS4 line (WITS / TRAINS, simple average of its HS6 lines), applied to
2025 import values. That is the bill if 2025 trade happened under the scenario's rules.

Rules of origin under GSP+: two-stage processing (fabric made in Bangladesh), where EBA accepts one stage.
Knitwear uses 80 to 90% local fabric, woven garments 35 to 40% (Financial Express, Dhaka Tribune).
So under GSP+ we assume 15% of knit value and 62.5% of woven value cannot claim the preference.

Volume: competitors that pay nothing (Vietnam under the EVFTA, India once its FTA is in force) make a duty a
price gap. We translate it with a constant elasticity of substitution between suppliers: lost share =
1 - (1 + effective duty) ** -sigma. sigma is unknown for this market, so we show 2 and 4 as a range.
"""

import duckdb
import pandas as pd

NOT_ORIGIN = {"Knit": 0.15, "Woven": 0.625}
SIGMA = (2.0, 4.0)

SCENARIOS = {
    "kept": {"label": "Access kept", "note": "EBA-style access continues through an extension or a trade deal"},
    "gsp_plus": {"label": "GSP+ granted", "note": "Duty-free, but only for garments that pass two-stage rules of origin, "
                 "and only if the apparel safeguard is not triggered"},
    "lost": {"label": "Access lost", "note": "Apparel pays the full MFN rate (standard GSP is cut for apparel because of Bangladesh's share)"},
}


def by_group(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    e = con.execute("select * from exposure_eu").df()
    rows = []
    for (group, fabric), g in e.groupby(["group", "fabric"]):
        value = g.value_eur.sum()
        mfn_duty = g.duty_eur_if_mfn.sum()
        duty = {"kept": 0.0, "gsp_plus": mfn_duty * NOT_ORIGIN[fabric], "lost": mfn_duty}
        for key, d in duty.items():
            eff = d / value
            rows.append({"group": group, "fabric": fabric, "scenario": key, "value_eur": value,
                         "mfn_rate": mfn_duty / value * 100, "duty_eur": d, "effective_rate": eff * 100,
                         "share_loss_low": (1 - (1 + eff) ** -SIGMA[0]) * 100,
                         "share_loss_high": (1 - (1 + eff) ** -SIGMA[1]) * 100})
    out = pd.DataFrame(rows)
    # One group can hold both knit and woven lines; combine them so the table has one row per group and scenario
    agg = out.groupby(["group", "scenario"], as_index=False).agg(value_eur=("value_eur", "sum"), duty_eur=("duty_eur", "sum"))
    agg["effective_rate"] = agg.duty_eur / agg.value_eur * 100
    for s, col in zip(SIGMA, ("share_loss_low", "share_loss_high"), strict=True):
        agg[col] = (1 - (1 + agg.effective_rate / 100) ** -s) * 100
    agg["exports_at_risk_low"] = agg.value_eur * agg.share_loss_low / 100
    agg["exports_at_risk_high"] = agg.value_eur * agg.share_loss_high / 100
    return agg


def totals(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    g = by_group(con)
    t = g.groupby("scenario", as_index=False)[["value_eur", "duty_eur", "exports_at_risk_low", "exports_at_risk_high"]].sum()
    t["effective_rate"] = t.duty_eur / t.value_eur * 100
    t["label"] = t.scenario.map(lambda s: SCENARIOS[s]["label"])
    return t
