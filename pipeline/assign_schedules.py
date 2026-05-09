# Match students to courses with affinity weighting
# Read: students.csv, courses_spring_2026_tagged.csv
# Write: schedules.csv (student_id, section_id, subject, course_code, component, is_anchor, units)
#
# Senior-priority, student-driven:
#   1. Sort students by year (seniors first), random tiebreak
#   2. Each picks a non-conflicting anchor weighted by school x level affinity
#      until within UNITS_BUFFER of their target_units
#   3. After each anchor, auto-assign least-full non-conflicting linked
#      section (DIS, LBS, etc) for that course

import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import STUDENTS, COURSES_TAGGED, SCHEDULES

STUDENTS_IN = STUDENTS
COURSES_IN = COURSES_TAGGED
SCHEDULES_OUT = SCHEDULES

SEED = 42
random.seed(SEED)


# School affinity: x5 same-school bonus, x1 otherwise
# Interdisc students never match so always x1 for them
SCHOOL_BONUS = 5.0

def school_affinity(student_school: str, course_school: str) -> float:
    if student_school == "hs_interdisc":
        return 1.0

    return SCHOOL_BONUS if student_school == course_school else 1.0

# Level affinity -- peaked at the year's expected level
# Edit LEVEL_WEIGHTS --  dial level influence up/down per year
YEAR_EXPECTED_LEVEL = {1: 0.5, 2: 1.0, 3: 2.0, 4: 2.5}
LEVEL_TO_NUM = {
    "seminar":  0.0,
    "intro":    1.0,
    "mid":      2.0,
    "advanced": 3.0,
    "unknown":  1.5,
}

# def level_affinity(student_year: int, course_level: str) -> float:
#     expected = YEAR_EXPECTED_LEVEL[student_year]
#     actual   = LEVEL_TO_NUM.get(course_level, 1.5)
#     dist = abs(expected - actual)

#     if dist <= 0.5: return 4.0
#     if dist <= 1.0: return 1.5
#     if dist <= 1.5: return 0.8
#     if dist <= 2.0: return 0.4

#     return 0.02

LEVEL_WEIGHTS = {
    # year: { level: weight }
    1: {"seminar": 1.5, "intro": 4.0, "mid": 1.0,  "advanced": 0.02},
    2: {"seminar": 0.5, "intro": 4.0, "mid": 3.0,  "advanced": 0.05},
    3: {"seminar": 0.07, "intro": 0.75, "mid": 4.0,  "advanced": 2.5},
    4: {"seminar": 0.07,"intro": 0.3, "mid": 3.0,  "advanced": 5.0},
    "unknown_default": 1.0,
}

def level_affinity(student_year, course_level):
    return LEVEL_WEIGHTS[student_year].get(course_level, LEVEL_WEIGHTS["unknown_default"])

# Per-(student, course) units sampling:
#   fixed (min == max) -> use that value
#   span <= 2 -> 70% take max, 30% max-1
#   wide span (research etc) -> 2 or 3 if in range, else midpoint
def sample_units(units_min, units_max) -> int:
    units_min = int(units_min)
    units_max = int(units_max)

    if units_min == units_max:
        return units_min
    
    span = units_max - units_min
    if span <= 2:
        return random.choices([units_max, units_max - 1], weights=[0.7, 0.3])[0]
    
    choices = [u for u in (2, 3) if units_min <= u <= units_max]
    if choices:
        return random.choice(choices)
    
    return (units_min + units_max) // 2


# Stop condition: students stop adding courses once within UNITS_BUFFER of target
# Big buffer = more undershoot, small = more overshoot
UNITS_BUFFER = 0


# Time / conflict helpers
def parse_time_to_minutes(t):
    # '3:00:00 PM' -> 900 (minutes from midnight), NaN -> None
    if not isinstance(t, str):
        return None
    try:
        dt = datetime.strptime(t.strip(), "%I:%M:%S %p")
        return dt.hour * 60 + dt.minute
    except ValueError:
        return None

def parse_days(s):
    if not isinstance(s, str):
        return []

    return [d.strip() for d in s.split(",") if d.strip()]

# both args: list of (day, start_min, end_min), true if any pair overlaps
def has_conflict(new_meetings, existing_meetings):
    for d_n, s_n, e_n in new_meetings:
        for d_e, s_e, e_e in existing_meetings:
            if d_n == d_e and s_n < e_e and s_e < e_n:
                return True

    return False


def main():
    # Load data
    students_df = pd.read_csv(STUDENTS_IN)
    courses_df  = pd.read_csv(COURSES_IN)
    print(f"Loaded {len(students_df)} students, {len(courses_df)} course rows")

    # per-section indexes
    section_meetings = defaultdict(list)  # section_id -> [(day, start, end), ...]
    section_info = {}  # section_id -> metadata dict

    for row in courses_df.itertuples(index=False):
        sid = row.section_id

        # Multiple rows per section_id (multi-meeting) all contribute meetings
        start = parse_time_to_minutes(row.start_time)
        end   = parse_time_to_minutes(row.end_time)

        if start is not None and end is not None:
            for d in parse_days(row.days):
                section_meetings[sid].append((d, start, end))

        if sid not in section_info:
            section_info[sid] = {
                "subject":       row.subject,
                "course_code":   row.course_code,
                "component":     row.component,
                "school":        row.school,
                "level":         row.level,
                "is_anchor":     bool(row.is_anchor),
                "units_min":     row.units_min,
                "units_max":     row.units_max,
                "curr_enrolled": int(row.curr_enrolled),
            }

    # Anchor sections: have students pick from these
    # skip anything with no scheduled meetings
    anchor_sids = [sid for sid, info in section_info.items() if info["is_anchor"] and section_meetings[sid]]
    print(f"Anchor sections with scheduled meetings: {len(anchor_sids)}")

    # Linked sections, group by (subject, course_code)
    linked_by_course = defaultdict(list)
    for sid, info in section_info.items():
        if not info["is_anchor"] and section_meetings[sid]:
            linked_by_course[(info["subject"], info["course_code"])].append(sid)

    # Seat tracking for anchors only
    # Don't cap sections -- not super real but whatevs
    # curr_enrolled is acceptable; least-full balancing too keep it reasonable
    SEAT_OVERFLOW = 1.15
    # seats_left = {sid: section_info[sid]["curr_enrolled"] for sid in anchor_sids}
    seats_left = {sid: int(section_info[sid]["curr_enrolled"] * SEAT_OVERFLOW) for sid in anchor_sids}
    # seats_left = {sid: section_info[sid]["max_enrolled"] for sid in anchor_sids}
    linked_assigned_count = defaultdict(int)  # for least-full sorting

    # sort students: seniors first, random tiebreak
    students_df = students_df.copy()
    students_df["_rand"] = [random.random() for _ in range(len(students_df))]
    students_df = students_df.sort_values(["year", "_rand"], ascending=[False, True]).drop(columns="_rand")

    # assignment loop
    schedule_records = []  # list of tuples for output
    actual_units_per_student = {}

    n_students = len(students_df)

    # Go through students + assign until target_units is close within UNITS_BUFFER
    for i, student in enumerate(students_df.itertuples(index=False)):
        # Progress print every 1000 students
        if i % 1000 == 0 and i > 0:
            print(f"  assigning student {i}/{n_students}...")

        my_meetings = []  # (day, start, end) tuples
        courses_taken = set()  # (subject, course_code)
        my_sections = []  # for output
        units_taken = 0  # track when to stop
        target = student.target_units

        while units_taken < target - UNITS_BUFFER:
            # Build candidate list of valid anchor sections
            candidates = []
            weights = []
            for asid in anchor_sids:
                # No seats left
                if seats_left[asid] <= 0:
                    continue

                info = anchor_meta = section_info[asid]
                # No repeating course
                if (info["subject"], info["course_code"]) in courses_taken:
                    continue
                # No time conflicts
                if has_conflict(section_meetings[asid], my_meetings):
                    continue

                # Weight = school_affinity x level_affinity
                w = (school_affinity(student.school, info["school"]) * level_affinity(student.year, info["level"]))
                candidates.append(asid)
                weights.append(w)

            if not candidates:
                break  # no more eligible courses

            # Randomly choose from candidates by weight
            chosen = random.choices(candidates, weights=weights, k=1)[0]
            chosen_info = section_info[chosen]
            u = sample_units(chosen_info["units_min"], chosen_info["units_max"])

            # Update info
            seats_left[chosen] -= 1
            units_taken += u
            courses_taken.add((chosen_info["subject"], chosen_info["course_code"]))
            my_sections.append(chosen)
            my_meetings.extend(section_meetings[chosen])

            schedule_records.append((
                student.id, chosen,
                chosen_info["subject"], chosen_info["course_code"],
                chosen_info["component"], True, u,
            ))

            # auto-assign linked section (least-full, non-conflicting)
            course_key = (chosen_info["subject"], chosen_info["course_code"])

            link_options = [
                lsid for lsid in linked_by_course.get(course_key, [])
                if not has_conflict(section_meetings[lsid], my_meetings)
            ]

            if link_options:
                link_options.sort(key=lambda x: linked_assigned_count[x])
                linked = link_options[0]
                linked_assigned_count[linked] += 1
                linked_info = section_info[linked]
                my_sections.append(linked)
                my_meetings.extend(section_meetings[linked])
                schedule_records.append((
                    student.id, linked,
                    linked_info["subject"], linked_info["course_code"],
                    linked_info["component"], False, 0,  # linked rows contribute 0 to unit count
                ))

        actual_units_per_student[student.id] = units_taken

        # TODO: Secondary loop to prevent students from being under 12 units:
        # MIN_UNITS = 12
        # while units_taken < MIN_UNITS:
        #     candidates = []
        #     for asid in anchor_sids:
        #         info = section_info[asid]

    out = pd.DataFrame(schedule_records, columns=[
        "student_id", "section_id", "subject", "course_code",
        "component", "is_anchor", "units",
    ])

    out.to_csv(SCHEDULES_OUT, index=False)
    print(f"\nWrote {len(out)} schedule rows to {SCHEDULES_OUT}")

    # ---- validation reports ----
    print("\n=== Validation ===")
    print(f"Schedule rows total:           {len(out)}")
    print(f"  Anchor enrollments:          {out['is_anchor'].sum()}")
    print(f"  Linked-section assignments:  {(~out['is_anchor']).sum()}")
    print(f"Students with >=1 course:      {out['student_id'].nunique()} / {len(students_df)}")

    units_series = pd.Series(actual_units_per_student)
    print(f"\nUnits per student: mean={units_series.mean():.2f}, "
          f"median={units_series.median()}, min={units_series.min()}, "
          f"max={units_series.max()}")
    print(f"Target units (from students.csv): mean={students_df['target_units'].mean():.2f}")

    courses_per_student = out.groupby("student_id")["is_anchor"].sum()
    print(f"Anchor courses per student: mean={courses_per_student.mean():.2f}, "
          f"median={courses_per_student.median()}")

    # Affinity sanity: % of (student, anchor) pairs that are same school
    out_anchors = out[out["is_anchor"]].merge(
        students_df[["id", "school"]].rename(columns={"school":"student_school"}),
        left_on="student_id", right_on="id"
    )

    out_anchors = out_anchors.merge(
        courses_df.drop_duplicates("section_id")[["section_id","school"]]
            .rename(columns={"school":"course_school"}),
        on="section_id"
    )
    same_school = (out_anchors["student_school"] == out_anchors["course_school"]).mean()
    print(f"\nSame-school enrollment fraction: {same_school:.1%}")
    print("(Random would be ~20-25% given school distribution; should be higher with affinity.)")

    # Year-level alignment
    print("\nLevel taken by year (% of each year's anchor enrollments):")
    out_anchors = out_anchors.merge(
        students_df[["id","year"]], left_on="student_id", right_on="id", suffixes=("","_y")
    )
    out_anchors = out_anchors.merge(
        courses_df.drop_duplicates("section_id")[["section_id","level"]],
        on="section_id"
    )
    pivot = pd.crosstab(out_anchors["year"], out_anchors["level"], normalize="index")
    print((pivot * 100).round(1))


if __name__ == "__main__":
    main()