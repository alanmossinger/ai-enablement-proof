# Data Directory

Raw and cached data files are git-ignored. They are downloaded via ingestion scripts.

## Structure

```
data/
  raw/          # Downloaded EIA-930, NOAA data (git-ignored)
  cache/        # Processed/intermediate files (git-ignored)
  audit/        # Immutable audit trail (JSONL) — committed
  README.md     # This file
```

## Data Sources

- **EIA-930 API v2** — register at https://www.eia.gov/opendata/register.php
- **NOAA/NWS API** — https://www.weather.gov/documentation/services-web-api
- **ERCOT public archives** — https://www.ercot.com/gridmktinfo/dashboards
