import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import COURSES_RAW

df = pd.read_csv(COURSES_RAW)

# See all unique building codes
buildings = df['building'].dropna().unique().tolist()
buildings = sorted(buildings)
for b in buildings:
    print(b)