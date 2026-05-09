# Generate N students with year, school, dorm (year-eligible), mode + speed, target units
# Reads dorm metadata from sim/map_buildings.py, writes data/processed/students.csv

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import STUDENTS
from sim.map_buildings import DORM_METADATA

N_STUDENTS = 6700  # TODO: check this matches total enrolled for spring quarter
RANDOM_SEED = 42

rng = np.random.default_rng(RANDOM_SEED)

YEAR_DIST = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}  # TODO: try again to find actual people in each year, not all data online??

# TODO: CHECK
# Distribution per school from 2024-25 Bachelor's degrees conferred
# https://facts.stanford.edu/academics/undergraduate-education/undergraduate-student-profile
# https://facts.stanford.edu/academics/undergraduate-education/class-2029-profile
# https://majors.stanford.edu/majors
SCHOOL_DIST = {
    "engineering":   0.40,
    "hs_interdisc":  0.25,
    "hs_social":     0.15,
    "hs_natural":    0.10,
    "hs_humanities": 0.08,
    "doerr":         0.02,
}

# Travel mode distribution + average speed (when assigning, have some variance)
MODE_DIST = {
    "walk":    0.25,
    "bike":    0.70,
    "electric": 0.05,
}

# in m/s
# MODE_SPEED = {
#     "walk":    1.5,    # ~3.35 mph
#     "bike":    5,    # ~11.2 mph 
#     "electric": 7,    # ~15.65 mph
# }
MODE_SPEED_RANGE = {
    "walk": (1.3, 1.7),  # ~2.9-3.8 mph
    "bike": (4.0, 5.8),  # ~9-13 mph
    "electric": (6.0, 8.0),  # ~13-18 mph
}


# Sample a dorm for a student of `year`, weighted by capacity (bigger dorms = more residents).
def sample_dorm(year, rng):
    eligible = [(name, m) for name, m in DORM_METADATA.items() if year in m["years"]]

    weights = np.array([m["capacity"] for _, m in eligible], dtype=float)
    probs = weights / weights.sum()
    idx = rng.choice(len(eligible), p=probs)
    return eligible[idx][0]


def generate_students(n, rng):
    rows = []
    
    year_keys = list(YEAR_DIST.keys())
    year_probs = list(YEAR_DIST.values())
    school_keys = list(SCHOOL_DIST.keys())
    school_probs = list(SCHOOL_DIST.values())
    mode_keys = list(MODE_DIST.keys())
    mode_probs = list(MODE_DIST.values())
    
    for i in range(n):
        year = int(rng.choice(year_keys, p=year_probs))
        school = rng.choice(school_keys, p=school_probs)
        dorm = sample_dorm(year, rng)
        mode = rng.choice(mode_keys, p=mode_probs)
        # speed = MODE_SPEED[mode]
        speed = round(rng.uniform(*MODE_SPEED_RANGE[mode]), 2)
        
        # Target units: clipped normal around 15 (what Stanford says is avg per quarter)
        # min = 12, max  = 20
        target_units = int(np.clip(rng.normal(15, 2), 12, 20))
        
        rows.append({
            "id": i,
            "year": year,
            "school": school,
            "dorm": dorm,
            "mode": mode,
            "speed": speed,
            "target_units": target_units,
        })
    
    return pd.DataFrame(rows)

def main():
    print(f"Generating {N_STUDENTS} students (seed={RANDOM_SEED})...")
    df = generate_students(N_STUDENTS, rng)

    df.to_csv(STUDENTS, index=False)
    print(f"Saved students.csv ({len(df)} rows)")

    # sanity prints
    print("\n-- Year distribution --")
    print(df['year'].value_counts().sort_index())

    print("\n-- School distribution --")
    print(df['school'].value_counts(normalize=True).sort_index().round(3))

    print("\n-- Mode distribution --")
    print(df['mode'].value_counts(normalize=True).sort_index().round(3))

    print("\n-- Top 10 dorms by population --")
    print(df['dorm'].value_counts().head(10))

    print("\n-- Target unit distribution --")
    print(df['target_units'].describe().round(1))

    print("\n-- Speed distribution by mode --")
    print(df.groupby('mode')['speed'].describe().round(2))

    # cross-check if frosh acc live in frosh dorms
    print("\n-- Dorm year-eligibility check --")
    for year in [1, 2, 3, 4]:
        students_year = df[df['year'] == year]
        violations = 0
        for _, row in students_year.iterrows():
            if year not in DORM_METADATA[row['dorm']]['years']:
                violations += 1
        print(f"  Year {year}: {len(students_year)} students, {violations} dorm violations")


if __name__ == "__main__":
    main()