# debug_columns.py
import pandas as pd
from pathlib import Path

print("=" * 60)
print("DEBUG: Checking column names in each dataset")
print("=" * 60)

# 1. Check headways
headways_path = Path("data/processed/route_headways.parquet")
if headways_path.exists():
    headways = pd.read_parquet(headways_path)
    print(f"\n1. headways.parquet columns ({len(headways)} rows):")
    print(f"   {list(headways.columns)}")
else:
    print("\n1. ❌ headways.parquet not found")

# 2. Check ridership
ridership_path = Path("data/synthetic/synthetic_ridership.parquet")
if ridership_path.exists():
    ridership = pd.read_parquet(ridership_path)
    print(f"\n2. synthetic_ridership.parquet columns ({len(ridership)} rows):")
    print(f"   {list(ridership.columns)}")
else:
    print("\n2. ❌ synthetic_ridership.parquet not found")

# 3. Check stops
gtfs_dir = Path("data/raw/ttc_gtfs")
stops_path = gtfs_dir / "stops.txt"
if stops_path.exists():
    stops = pd.read_csv(stops_path)
    print(f"\n3. stops.txt columns ({len(stops)} rows):")
    print(f"   {list(stops.columns)}")
else:
    print("\n3. ❌ stops.txt not found")

print("\n" + "=" * 60)