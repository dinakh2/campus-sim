import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from paths import OUTPUTS

df = pd.read_parquet(OUTPUTS / "trajectory.parquet")
print(f"Total trajectory rows: {len(df)}")
print(f"Unique agents: {df['agent_id'].nunique()}")
print(f"\nStatus breakdown:")
print(df["status"].value_counts())
print(f"\nMoving rows by hour:")
df["hour"] = df["t"] // 3600
print(df[df["status"]=="moving"].groupby("hour").size())