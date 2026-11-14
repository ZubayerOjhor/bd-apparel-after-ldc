"""python -m apparel [fetch|build|export|all]"""

import sys

from . import build, checks, export, fetch
from .config import MARKETS


def main(step: str) -> None:
    if step in ("fetch", "all"):
        fetch.eurostat_annual(), fetch.eurostat_annual_hs2(), fetch.eurostat_monthly(), fetch.eur_usd()
        fetch.wits_mfn("EU", build.TARIFF_YEAR), fetch.wits_mfn("US", build.TARIFF_YEAR)
        for m, spec in MARKETS.items():
            if spec["source"] == "comtrade":
                fetch.comtrade(m)
                print("fetched", m)
    if step in ("build", "export", "all"):
        con = build.run()
        results = checks.run(con)
        for r in results:
            print("PASS" if r.ok else "FAIL", r.name, "|", r.detail)
        if not all(r.ok for r in results):
            raise SystemExit("Data checks failed: nothing exported.")
        if step in ("export", "all"):
            d = export.write(con)
            print("wrote dashboard/data/apparel.json,", len(d["share_group"]), "share rows")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
