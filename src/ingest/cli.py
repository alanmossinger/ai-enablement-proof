"""CLI for data ingestion — EIA-930 and NOAA weather data.

Usage:
    python -m src.ingest.cli demand --start 2021-02-01 --end 2021-02-28 --ba ERCO
    python -m src.ingest.cli fuel --start 2021-02-01 --end 2021-02-28 --ba ERCO
    python -m src.ingest.cli interchange --start 2021-02-01 --end 2021-02-28 --ba ERCO
    python -m src.ingest.cli weather-forecast --ba ERCO
    python -m src.ingest.cli backfill-uri   # convenience: fetch all Uri-period data
"""

from __future__ import annotations

import argparse
import logging
import sys

from .eia930 import ingest_demand, ingest_fuel_type, ingest_interchange
from .noaa import ingest_nws_forecasts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Key backtest periods
URI_START = "2021-02-08"
URI_END = "2021-02-25"
URI_BAS = ["ERCO"]

ELLIOTT_START = "2022-12-20"
ELLIOTT_END = "2023-01-05"
ELLIOTT_BAS = ["PJM", "MISO", "NYIS", "ISNE"]


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-Enablement-Proof data ingestion")
    sub = parser.add_subparsers(dest="command")

    # Demand
    p_demand = sub.add_parser("demand", help="Ingest EIA-930 demand data")
    p_demand.add_argument("--start", required=True)
    p_demand.add_argument("--end", required=True)
    p_demand.add_argument("--ba", nargs="*", default=None)
    p_demand.add_argument("--db", default="data/grid.duckdb")

    # Fuel
    p_fuel = sub.add_parser("fuel", help="Ingest EIA-930 fuel-type data")
    p_fuel.add_argument("--start", required=True)
    p_fuel.add_argument("--end", required=True)
    p_fuel.add_argument("--ba", nargs="*", default=None)
    p_fuel.add_argument("--db", default="data/grid.duckdb")

    # Interchange
    p_ix = sub.add_parser("interchange", help="Ingest EIA-930 interchange data")
    p_ix.add_argument("--start", required=True)
    p_ix.add_argument("--end", required=True)
    p_ix.add_argument("--ba", nargs="*", default=None)
    p_ix.add_argument("--db", default="data/grid.duckdb")

    # NWS forecasts
    p_wx = sub.add_parser("weather-forecast", help="Ingest NWS hourly forecasts")
    p_wx.add_argument("--ba", nargs="*", default=None)
    p_wx.add_argument("--db", default="data/grid.duckdb")

    # Backfill shortcuts
    sub.add_parser("backfill-uri", help="Backfill all data for Winter Storm Uri period")
    sub.add_parser("backfill-elliott", help="Backfill all data for Winter Storm Elliott period")

    args = parser.parse_args()

    if args.command == "demand":
        n = ingest_demand(args.start, args.end, args.ba, args.db)
        logger.info("Done: %d demand records ingested", n)

    elif args.command == "fuel":
        n = ingest_fuel_type(args.start, args.end, args.ba, args.db)
        logger.info("Done: %d fuel records ingested", n)

    elif args.command == "interchange":
        n = ingest_interchange(args.start, args.end, args.ba, args.db)
        logger.info("Done: %d interchange records ingested", n)

    elif args.command == "weather-forecast":
        n = ingest_nws_forecasts(args.ba, args.db)
        logger.info("Done: %d forecast records ingested", n)

    elif args.command == "backfill-uri":
        logger.info("Backfilling Winter Storm Uri period (%s to %s)", URI_START, URI_END)
        n1 = ingest_demand(URI_START, URI_END, URI_BAS)
        n2 = ingest_fuel_type(URI_START, URI_END, URI_BAS)
        n3 = ingest_interchange(URI_START, URI_END, URI_BAS)
        logger.info("Uri backfill complete: %d demand, %d fuel, %d interchange", n1, n2, n3)

    elif args.command == "backfill-elliott":
        logger.info(
            "Backfilling Winter Storm Elliott period (%s to %s)", ELLIOTT_START, ELLIOTT_END
        )
        n1 = ingest_demand(ELLIOTT_START, ELLIOTT_END, ELLIOTT_BAS)
        n2 = ingest_fuel_type(ELLIOTT_START, ELLIOTT_END, ELLIOTT_BAS)
        n3 = ingest_interchange(ELLIOTT_START, ELLIOTT_END, ELLIOTT_BAS)
        logger.info("Elliott backfill complete: %d demand, %d fuel, %d interchange", n1, n2, n3)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
