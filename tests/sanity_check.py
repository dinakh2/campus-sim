# scratch/sanity_check.py — run from project root
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sim.map_buildings import (
    DORM_LOCATIONS, DORM_METADATA, BUILDING_LOCATIONS, get_building_location
)
from paths import STUDENTS, COURSES_TAGGED

students = pd.read_csv(STUDENTS)
courses  = pd.read_csv(COURSES_TAGGED)

# === Dorm key check ===
print("=" * 60)
print("DORMS")
print("=" * 60)
student_dorms = set(students["dorm"].dropna().unique())
loc_dorms     = set(DORM_LOCATIONS.keys())

missing_loc = student_dorms - loc_dorms
if missing_loc:
    print(f"!! {len(missing_loc)} dorms in students.csv NOT in DORM_LOCATIONS:")
    for d in sorted(missing_loc):
        print(f"   - {d!r}  ({(students['dorm'] == d).sum()} students)")
else:
    print(f"[OK] All {len(student_dorms)} dorms in students.csv have coordinates")

unused = loc_dorms - student_dorms
if unused:
    print(f"\n   {len(unused)} dorms in DORM_LOCATIONS not used in students.csv (probably fine)")

# === Building key check ===
print()
print("=" * 60)
print("BUILDINGS")
print("=" * 60)

# Filter to real meetings: anchor sections that students will actually go to
classroom = courses[courses["is_anchor"]].dropna(subset=["building","start_time","days"])
print(f"Total scheduled classroom meetings (anchor + has time/place): {len(classroom)}")

# What fraction of those buildings does get_building_location() resolve?
unique_bldgs = classroom["building"].unique()
resolved = []
unresolved = []
for _, row in classroom.iterrows():
    b = row["building"]
    subj = row["subject"]
    try:
        loc = get_building_location(b, subj)
        if loc is None:
            unresolved.append(b)
        else:
            resolved.append(b)
    except Exception as e:
        unresolved.append(b)

print(f"Unique buildings referenced: {len(unique_bldgs)}")
print(f"   Resolved by get_building_location: {len(resolved)}")
print(f"   Unresolved:                        {len(unresolved)}")

# Weight unresolved by enrollment — what fraction of student-class assignments are affected?
if unresolved:
    affected_meetings = classroom[classroom["building"].isin(unresolved)]
    affected_enroll   = affected_meetings["curr_enrolled"].sum()
    total_enroll      = classroom["curr_enrolled"].sum()
    print(f"   Enrollment in unresolved buildings: {affected_enroll} / {total_enroll}"
          f" ({affected_enroll/total_enroll*100:.1f}%)")
    print(f"\n   Top unresolved buildings by enrollment:")
    bad = (affected_meetings.groupby("building")["curr_enrolled"]
           .sum().sort_values(ascending=False).head(15))
    for b, n in bad.items():
        print(f"     {n:5d}  {b}")

# Replace the schedules-integrity block at the bottom with this:

print()
print("=" * 60)
print("SCHEDULES")
print("=" * 60)

sched = pd.read_csv("data/processed/schedules.csv")

schedule_section_ids = set(sched["section_id"].unique())
course_section_ids   = set(courses["section_id"].unique())
orphans = schedule_section_ids - course_section_ids
if orphans:
    print(f"!! {len(orphans)} section_ids in schedules.csv don't exist in courses_tagged.csv")
else:
    print(f"[OK] Every section_id in schedules.csv exists in courses_tagged.csv")

# Use sched's own is_anchor column directly — schedules.csv already has it
sched_anchor = sched[sched["is_anchor"] == True].copy()

# Pull building from courses (not is_anchor — already have that)
bldg_lookup = courses.drop_duplicates("section_id")[["section_id", "building"]]
sched_anchor = sched_anchor.merge(bldg_lookup, on="section_id", how="left")

unresolved_set = set(unresolved)
lost_meetings = sched_anchor[sched_anchor["building"].isin(unresolved_set)]
affected_students = lost_meetings["student_id"].nunique()
total_students = sched["student_id"].nunique()
print(f"\nStudents with at least one class in an unresolved building: "
      f"{affected_students} / {total_students} ({affected_students/total_students*100:.1f}%)")

# Also useful: how many anchor meetings get dropped entirely?
total_anchor_meetings = len(sched_anchor)
lost = len(lost_meetings)
print(f"Anchor meetings in unresolved buildings: {lost} / {total_anchor_meetings} "
      f"({lost/total_anchor_meetings*100:.1f}%)")