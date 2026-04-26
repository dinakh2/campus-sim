import pandas as pd

df = pd.read_csv("courses_2025_2026.csv")

# See all unique building codes
buildings = df['building'].dropna().unique().tolist()
buildings = sorted(buildings)
for b in buildings:
    print(b)