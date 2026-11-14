"""Scope of the study: who competes, in which markets, on which products."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "ref"
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

YEARS = list(range(2015, 2026))  # full calendar years in every source

# Exporters we compare. Codes are UN M49 (Comtrade) and ISO-2 (Eurostat).
EXPORTERS = {
    "BD": {"name": "Bangladesh", "m49": 50},
    "VN": {"name": "Vietnam", "m49": 704},
    "KH": {"name": "Cambodia", "m49": 116},
    "IN": {"name": "India", "m49": 699},
    "CN": {"name": "China", "m49": 156},
}
WORLD_M49 = 0

# Import markets. The EU comes from Eurostat; the rest from UN Comtrade (reported by the importer).
MARKETS = {
    "EU": {"name": "European Union", "source": "eurostat"},
    "US": {"name": "United States", "source": "comtrade", "m49": 842},
    "UK": {"name": "United Kingdom", "source": "comtrade", "m49": 826},
    "CA": {"name": "Canada", "source": "comtrade", "m49": 124},
    "JP": {"name": "Japan", "source": "comtrade", "m49": 392},
    "AU": {"name": "Australia", "source": "comtrade", "m49": 36},
}

# HS chapters 61 (knitted) and 62 (woven) at 4 digits, grouped into product groups a buyer would recognise.
PRODUCT_GROUPS = {
    "Outerwear": ["6101", "6102", "6201", "6202"],
    "Suits, trousers and shorts, knit": ["6103", "6104"],
    "Trousers and shorts, woven": ["6203", "6204"],
    "Shirts and blouses": ["6105", "6106", "6205", "6206"],
    "Underwear and nightwear": ["6107", "6108", "6207", "6208"],
    "T-shirts and vests": ["6109"],
    "Sweaters and sweatshirts": ["6110"],
    "Babywear": ["6111", "6209"],
    "Sportswear and swimwear": ["6112", "6211"],
    "Other garments and accessories": ["6113", "6114", "6115", "6116", "6117", "6210", "6212", "6213",
                                       "6214", "6215", "6216", "6217"],
}
HS4 = sorted(h for codes in PRODUCT_GROUPS.values() for h in codes)
GROUP_OF = {h: g for g, codes in PRODUCT_GROUPS.items() for h in codes}
