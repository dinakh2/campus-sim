# verify_data.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim.map_buildings import DORM_METADATA, DORM_LOCATIONS

# Every dorm in metadata should have a location
missing_loc = [k for k in DORM_METADATA if k not in DORM_LOCATIONS]
print(f"Dorms in metadata but missing location: {missing_loc}")

# Every dorm in locations should have metadata (or it's a stale entry to clean up)
missing_meta = [k for k in DORM_LOCATIONS if k not in DORM_METADATA]
print(f"Dorms with location but no metadata (stale?): {missing_meta}")

# Total capacity should be ~6,660
total = sum(m['capacity'] for m in DORM_METADATA.values())
print(f"Total housing capacity: {total}")

# Capacity by year
for y in [1, 2, 3, 4]:
    cap = sum(m['capacity'] for m in DORM_METADATA.values() if y in m['years'])
    print(f"  Year {y} eligible capacity: {cap}")