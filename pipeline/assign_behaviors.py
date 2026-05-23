# Assign per-agent behavior attributes to each student
#
# Read: data/processed/students.csv
# Write: data/processed/students_with_behaviors.csv
#
# Sim run order:
#   1. pipeline/tag_courses.py
#   2. pipeline/generate_population.py -> students.csv
#   3. pipeline/assign_schedules.py -> schedules.csv
#   4. pipeline/assign_behaviors.py -> students_with_behaviors.csv
#   5. sim/runner.py + eval/congestion.py

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import STUDENTS, STUDENTS_EXTENDED
from sim.map_buildings import DORM_LOCATIONS, DORM_METADATA, ALL_LOCATIONS
from pipeline import behavior_params as bp


# ---------- Distance helpers ----------

# Rough haversine distance in meters between (lat, lon) pairs
def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# approx walking travel time at population-average walk speed
WALK_SPEED_FOR_WEIGHTING_MPS = 1.5

def walk_min(meters: float) -> float:
    return meters / WALK_SPEED_FOR_WEIGHTING_MPS / 60.0


# Get (lat, lon) for a building/dorm/dining key, None if nf
def location_of(key: str) -> tuple[float, float] | None:
    loc = ALL_LOCATIONS.get(key)
    if loc is None:
        return None
    return (loc[1], loc[2])


# ---------- Coffee destination assignment ----------

def pick_coffee_destination(rng: np.random.Generator, school: str, dorm: str) -> str:
    dorm_loc = location_of(dorm)
    if dorm_loc is None:
        # Fallback: uniform pick if we can't resolve the dorm (shouldn't happen)
        return str(rng.choice(bp.COFFEE_DESTINATIONS))

    school_affinity = bp.SCHOOL_COFFEE_AFFINITY.get(school, {})

    weights = []
    for dest in bp.COFFEE_DESTINATIONS:
        dest_loc = location_of(dest)
        if dest_loc is None:
            weights.append(0.0)
            continue
        travel = walk_min(haversine_m(dorm_loc[0], dorm_loc[1], dest_loc[0], dest_loc[1]))
        proximity = math.exp(-travel / bp.COFFEE_DISTANCE_DECAY_SCALE_MIN)
        affinity = school_affinity.get(dest, 1.0)
        weights.append(proximity * affinity)

    weights = np.array(weights, dtype=float)
    if weights.sum() == 0:
        return str(rng.choice(bp.COFFEE_DESTINATIONS))
    probs = weights / weights.sum()
    return str(rng.choice(bp.COFFEE_DESTINATIONS, p=probs))


# ---------- Lunch destination pools ----------

def pick_lunch_eateries(rng: np.random.Generator, dorm: str) -> list[str]:
    dorm_loc = location_of(dorm)
    if dorm_loc is None:
        idxs = rng.choice(len(bp.LUNCH_EATERIES), bp.LUNCH_EATERIES_PER_AGENT, replace=False)
        return [bp.LUNCH_EATERIES[i] for i in idxs]

    # Weight by inverse distance from dorm
    weights = []
    for eatery in bp.LUNCH_EATERIES:
        loc = location_of(eatery)
        if loc is None:
            weights.append(0.0)
            continue
        travel = walk_min(haversine_m(dorm_loc[0], dorm_loc[1], loc[0], loc[1]))
        weights.append(math.exp(-travel / bp.LUNCH_DISTANCE_DECAY_SCALE_MIN))

    weights = np.array(weights, dtype=float)
    if weights.sum() == 0:
        idxs = rng.choice(len(bp.LUNCH_EATERIES), bp.LUNCH_EATERIES_PER_AGENT, replace=False)
        return [bp.LUNCH_EATERIES[i] for i in idxs]

    probs = weights / weights.sum()
    n_pick = min(bp.LUNCH_EATERIES_PER_AGENT, len(bp.LUNCH_EATERIES))
    idxs = rng.choice(len(bp.LUNCH_EATERIES), n_pick, replace=False, p=probs)
    return [bp.LUNCH_EATERIES[i] for i in idxs]


def pick_lunch_dining_halls(rng: np.random.Generator, dorm: str) -> list[str]:
    complex_name = DORM_METADATA.get(dorm, {}).get("complex")
    primary_hall = bp.DORM_COMPLEX_PRIMARY_HALL.get(complex_name)

    picks: list[str] = []
    if primary_hall and primary_hall in bp.LUNCH_DINING_HALLS:
        picks.append(primary_hall)

    # Fill remaining slots with the closest other halls (weighted)
    dorm_loc = location_of(dorm)
    candidates = [h for h in bp.LUNCH_DINING_HALLS if h not in picks]

    if dorm_loc is None or not candidates:
        # Fallback: random fill
        remaining = bp.LUNCH_DINING_HALLS_PER_AGENT - len(picks)
        if remaining > 0 and candidates:
            extras = rng.choice(candidates,
                                 min(remaining, len(candidates)),
                                 replace=False)
            picks.extend(str(e) for e in extras)
        return picks

    weights = []
    for hall in candidates:
        loc = location_of(hall)
        if loc is None:
            weights.append(0.0)
            continue
        travel = walk_min(haversine_m(dorm_loc[0], dorm_loc[1], loc[0], loc[1]))
        weights.append(math.exp(-travel / bp.LUNCH_DISTANCE_DECAY_SCALE_MIN))

    weights = np.array(weights, dtype=float)
    remaining = bp.LUNCH_DINING_HALLS_PER_AGENT - len(picks)
    if remaining > 0 and weights.sum() > 0:
        probs = weights / weights.sum()
        idxs = rng.choice(len(candidates), min(remaining, len(candidates)),
                          replace=False, p=probs)
        picks.extend(candidates[i] for i in idxs)

    return picks


# ---------- Library destination assignment ----------

def pick_library_destinations(rng: np.random.Generator, school: str, dorm: str) -> list[str]:
    dorm_loc = location_of(dorm)
    school_aff = bp.LIBRARY_SCHOOL_AFFINITY.get(school, {})

    if dorm_loc is None:
        idxs = rng.choice(len(bp.LIBRARY_DESTINATIONS),
                          bp.LIBRARY_DESTINATIONS_PER_AGENT, replace=False)
        return [bp.LIBRARY_DESTINATIONS[i] for i in idxs]

    weights = []
    for lib in bp.LIBRARY_DESTINATIONS:
        loc = location_of(lib)
        if loc is None:
            weights.append(0.0)
            continue
        travel = walk_min(haversine_m(dorm_loc[0], dorm_loc[1], loc[0], loc[1]))
        # Reuse the lunch distance decay scale -- same shape applies.
        proximity = math.exp(-travel / bp.LUNCH_DISTANCE_DECAY_SCALE_MIN)
        affinity = school_aff.get(lib, 1.0)
        weights.append(proximity * affinity)

    weights = np.array(weights, dtype=float)
    if weights.sum() == 0:
        idxs = rng.choice(len(bp.LIBRARY_DESTINATIONS),
                          bp.LIBRARY_DESTINATIONS_PER_AGENT, replace=False)
        return [bp.LIBRARY_DESTINATIONS[i] for i in idxs]

    probs = weights / weights.sum()
    n_pick = min(bp.LIBRARY_DESTINATIONS_PER_AGENT, len(bp.LIBRARY_DESTINATIONS))
    idxs = rng.choice(len(bp.LIBRARY_DESTINATIONS), n_pick, replace=False, p=probs)
    return [bp.LIBRARY_DESTINATIONS[i] for i in idxs]


# ---------- Gym destination ----------

# Nearest gym to dorm
def pick_gym_destination(dorm: str) -> str:
    dorm_loc = location_of(dorm)
    if dorm_loc is None:
        return bp.GYM_DESTINATIONS[0]

    best, best_d = None, float("inf")

    for g in bp.GYM_DESTINATIONS:
        loc = location_of(g)
        if loc is None:
            continue
        d = haversine_m(dorm_loc[0], dorm_loc[1], loc[0], loc[1])
        if d < best_d:
            best_d, best = d, g

    return best or bp.GYM_DESTINATIONS[0]


# ---------- Main attribute assign ----------

def assign_for_student(row: pd.Series, rng: np.random.Generator) -> dict:
    school = str(row["school"])
    dorm = str(row["dorm"])

    # Coffee
    drinker_rate = bp.COFFEE_DRINKER_RATE_BY_SCHOOL.get(school, bp.COFFEE_DRINKER_RATE_DEFAULT)
    is_coffee_drinker = bool(rng.random() < drinker_rate)
    is_early_riser = bool(rng.random() < bp.EARLY_RISER_RATE)
    coffee_destination = pick_coffee_destination(rng, school, dorm) if is_coffee_drinker else ""
    coffee_duration_min = int(round(max(2, rng.normal(bp.COFFEE_GRAB_DURATION_MIN_MEAN, bp.COFFEE_GRAB_DURATION_MIN_STD))))

    # Lunch
    lunch_eateries = pick_lunch_eateries(rng, dorm)
    lunch_dining_halls = pick_lunch_dining_halls(rng, dorm)
    lunch_will_go_dorm = bool(rng.random() < bp.LUNCH_WILL_GO_DORM_RATE)
    lunch_duration_min = int(round(max(10, rng.normal(bp.LUNCH_DURATION_MIN_MEAN, bp.LUNCH_DURATION_MIN_STD))))
    lunch_avanti_eligible = dorm in bp.AVANTI_ELIGIBLE_DORMS
    lunch_yme_eligible = dorm in bp.YME_ELIGIBLE_DORMS

    # Home return
    home_return_threshold_min = int(round(max(30, rng.normal(
        bp.HOME_RETURN_THRESHOLD_MEAN_MIN, bp.HOME_RETURN_THRESHOLD_STD_MIN))))

    library_use_rate = max(0.0, min(1.0,
        bp.LIBRARY_USE_RATE_BASE + bp.LIBRARY_USE_RATE_SCHOOL_DELTA.get(school, 0.0)))
    library_destinations = pick_library_destinations(rng, school, dorm)

    eats_dinner_on_campus = bool(rng.random() < bp.DINNER_ON_CAMPUS_RATE)
    dinner_duration_min = int(round(max(15, rng.normal(bp.DINNER_DURATION_MIN_MEAN, bp.DINNER_DURATION_MIN_STD))))

    gym_days_keys = list(bp.GYM_DAYS_PER_WEEK_DIST.keys())
    gym_days_probs = list(bp.GYM_DAYS_PER_WEEK_DIST.values())
    gym_days_per_week = int(rng.choice(gym_days_keys, p=gym_days_probs))
    gym_destination = pick_gym_destination(dorm)
    gym_duration_min = int(round(max(20, rng.normal(bp.GYM_DURATION_MIN_MEAN, bp.GYM_DURATION_MIN_STD))))

    return {
        "is_early_riser": is_early_riser,
        "is_coffee_drinker": is_coffee_drinker,
        "coffee_destination": coffee_destination,
        "coffee_duration_min": coffee_duration_min,
        "eats_lunch_on_campus_base": bp.LUNCH_ON_CAMPUS_RATE,
        "lunch_eateries": "|".join(lunch_eateries),
        "lunch_dining_halls": "|".join(lunch_dining_halls),
        "lunch_will_go_dorm": lunch_will_go_dorm,
        "lunch_duration_min": lunch_duration_min,
        "lunch_avanti_eligible": lunch_avanti_eligible,
        "lunch_yme_eligible": lunch_yme_eligible,
        "home_return_threshold_min": home_return_threshold_min,

        "library_use_rate": round(library_use_rate, 3),
        "library_destinations": "|".join(library_destinations),

        "eats_dinner_on_campus": eats_dinner_on_campus,
        "dinner_duration_min": dinner_duration_min,

        "gym_days_per_week": gym_days_per_week,
        "gym_destination": gym_destination,
        "gym_duration_min": gym_duration_min,
    }


def main():
    print(f"Loading {STUDENTS}...")
    df = pd.read_csv(STUDENTS)
    print(f"  {len(df)} students")

    rng = np.random.default_rng(bp.BEHAVIOR_RNG_SEED)

    new_cols = [assign_for_student(row, rng) for _, row in df.iterrows()]
    extra_df = pd.DataFrame(new_cols)
    out = pd.concat([df.reset_index(drop=True), extra_df.reset_index(drop=True)], axis=1)

    out.to_csv(STUDENTS_EXTENDED, index=False)
    print(f"Wrote {STUDENTS_EXTENDED} ({len(out)} rows, {len(out.columns)} cols)")

    # Sanity
    print("\n-- Coffee drinker rate, by school --")
    print(out.groupby("school")["is_coffee_drinker"].mean().round(3).sort_values(ascending=False))

    print("\n-- Early riser rate --")
    print(f"  {out['is_early_riser'].mean():.3f}")

    print("\n-- Top coffee destinations --")
    coffee = out[out["is_coffee_drinker"]]["coffee_destination"].value_counts().head(8)
    print(coffee)

    print("\n-- Avanti / YME eligibility --")
    print(f"  Avanti: {int(out['lunch_avanti_eligible'].sum())} agents")
    print(f"  YME:    {int(out['lunch_yme_eligible'].sum())} agents")

    print("\n-- Home return threshold (min) --")
    print(out["home_return_threshold_min"].describe().round(1))

    print("\n-- Library use rate, by school --")
    print(out.groupby("school")["library_use_rate"].mean().round(3).sort_values(ascending=False))

    print("\n-- Dinner on campus rate --")
    print(f"  {out['eats_dinner_on_campus'].mean():.3f}")

    print("\n-- Gym days/week distribution --")
    print(out["gym_days_per_week"].value_counts().sort_index())

    print("\n-- Gym destination split --")
    print(out["gym_destination"].value_counts())

    print("\n-- Sample agent --")
    s = out.iloc[0]
    for col in ["id", "year", "school", "dorm", "is_early_riser", "is_coffee_drinker",
                "coffee_destination", "lunch_eateries", "lunch_dining_halls",
                "lunch_will_go_dorm", "lunch_duration_min", "home_return_threshold_min",
                "library_use_rate", "library_destinations",
                "eats_dinner_on_campus", "dinner_duration_min",
                "gym_days_per_week", "gym_destination", "gym_duration_min"]:
        print(f"  {col}: {s[col]}")


if __name__ == "__main__":
    main()
