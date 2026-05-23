# BUILD PER-AGENT DATA FROM CSV OUTPUTS
#
# Public API:
# load_agents() -> list[AgentData]
#     Return ready-to-instantiate agent records, with all data resolved
#     (dorm coords, class meeting coords, parsed times). Skips meetings if location
#     can't be resolved.
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import STUDENTS, STUDENTS_EXTENDED, SCHEDULES, COURSES_TAGGED
from sim.map_buildings import DORM_LOCATIONS, get_building_location

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Single class meeting on a single day, fully resolved (building name + lat/lon, parsed time)
@dataclass
class Meeting:
    section_id: str
    subject: str
    course_code: str
    component: str
    is_anchor: bool
    day: str
    start_sec: int  # seconds from midnight
    end_sec: int
    building_name: str
    lat: float
    lon: float

# All student info for an Agent
@dataclass
class AgentData:
    student_id: str
    year: int
    school: str
    mode: str
    speed: float

    # Home location
    dorm_name: str
    dorm_lat: float
    dorm_lon: float

    # Schedule: list of meetings
    meetings: list[Meeting] = field(default_factory=list)

    # ----- Behavior attributes (from pipeline/assign_behaviors.py) -----
    # If students_with_behaviors.csv loaded, populate

    is_early_riser: bool = False
    is_coffee_drinker: bool = False
    coffee_destination: str = ""
    coffee_duration_min: int = 8

    eats_lunch_on_campus_base: float = 0.0
    lunch_eateries: list[str] = field(default_factory=list)
    lunch_dining_halls: list[str] = field(default_factory=list)
    lunch_will_go_dorm: bool = False
    lunch_duration_min: int = 30
    lunch_avanti_eligible: bool = False
    lunch_yme_eligible: bool = False

    home_return_threshold_min: int = 10_000  # p much disabled

    library_use_rate: float = 0.0
    library_destinations: list[str] = field(default_factory=list)

    eats_dinner_on_campus: bool = False
    dinner_duration_min: int = 40

    gym_days_per_week: int = 0
    gym_destination: str = ""
    gym_duration_min: int = 60

# Time to seconds from midnight
def _parse_time_to_sec(t: str | float) -> int | None:
    if not isinstance(t, str):
        return None
    try:
        dt = datetime.strptime(t.strip(), "%I:%M:%S %p")
        return dt.hour * 3600 + dt.minute * 60 + dt.second
    except ValueError:
        return None

def _parse_days(s: str | float) -> list[str]:
    if not isinstance(s, str):
        return []
    return [d.strip() for d in s.split(",") if d.strip() in WEEKDAYS]

# ("Tresidder|CODAB|Forbes") -> list[str]
def _parse_pipe_list(cell) -> list[str]:
    if not isinstance(cell, str) or not cell:
        return []
    
    return [p for p in cell.split("|") if p]

def load_agents() -> list[AgentData]:
    if STUDENTS_EXTENDED.exists():
        students = pd.read_csv(STUDENTS_EXTENDED)
        has_behaviors = True
        print(f"  Using {STUDENTS_EXTENDED.name} (behaviors enabled)")
    else:
        students = pd.read_csv(STUDENTS)
        has_behaviors = False
        print(f"  Using {STUDENTS.name} (no behaviors; run pipeline/assign_behaviors.py to enable)")
    schedules = pd.read_csv(SCHEDULES)
    courses = pd.read_csv(COURSES_TAGGED)

    # One row per (section_id) for building/time info
    course_meetings = courses[
        ["section_id", "subject", "course_code", "component", "is_anchor",
         "building", "days", "start_time", "end_time"]
    ].copy()

    # Resolve building once per (section_id, building, subject)
    print(f"Resolving buildings for {len(course_meetings)} meeting rows...")
    locations: dict[tuple[str, str], tuple[str, float, float] | None] = {}
    resolved_meetings: list[Meeting] = []

    skipped_no_time = 0
    skipped_no_loc = 0

    for row in course_meetings.itertuples(index=False):
        start = _parse_time_to_sec(row.start_time)
        end = _parse_time_to_sec(row.end_time)
        days = _parse_days(row.days)

        if start is None or end is None or not days:
            skipped_no_time += 1
            continue

        # Cache (building, subject) -> location lookup
        key = (str(row.building), row.subject)
        if key not in locations:
            locations[key] = get_building_location(row.building, row.subject)
        loc = locations[key]

        if loc is None:
            skipped_no_loc += 1
            continue

        bldg_name, lat, lon = loc

        # Expand multi-day meeting to one meeting/day
        for day in days:
            resolved_meetings.append(Meeting(
                section_id=row.section_id,
                subject=row.subject,
                course_code=str(row.course_code),
                component=row.component,
                is_anchor=bool(row.is_anchor),
                day=day,
                start_sec=start,
                end_sec=end,
                building_name=bldg_name,
                lat=lat,
                lon=lon,
            ))

    print(f"  Resolved: {len(resolved_meetings)} day-instances of meetings")
    print(f"  Skipped (no time/days): {skipped_no_time}")
    print(f"  Skipped (no location):  {skipped_no_loc}")

    # Index meetings by section_id for join
    meetings_by_section: dict[str, list[Meeting]] = {}
    for m in resolved_meetings:
        meetings_by_section.setdefault(m.section_id, []).append(m)

    # Build agents
    print(f"\nBuilding {len(students)} agents...")
    agents: list[AgentData] = []
    missing_dorm = 0

    for s in students.itertuples(index=False):
        if s.dorm not in DORM_LOCATIONS:
            missing_dorm += 1
            continue
        dorm_name, dorm_lat, dorm_lon = DORM_LOCATIONS[s.dorm]

        # Get curr student's sections from schedules.csv
        my_sections = schedules[schedules["student_id"] == s.id]["section_id"].tolist()
        my_meetings: list[Meeting] = []
        for sid in my_sections:
            my_meetings.extend(meetings_by_section.get(sid, []))

        # behavior attributes if STUDENTS_EXTENDED loaded
        behavior_kwargs = {}
        if has_behaviors:
            behavior_kwargs = {
                "is_early_riser":            bool(s.is_early_riser),
                "is_coffee_drinker":         bool(s.is_coffee_drinker),
                "coffee_destination":        str(s.coffee_destination) if isinstance(s.coffee_destination, str) else "",
                "coffee_duration_min":       int(s.coffee_duration_min),
                "eats_lunch_on_campus_base": float(s.eats_lunch_on_campus_base),
                "lunch_eateries":            _parse_pipe_list(s.lunch_eateries),
                "lunch_dining_halls":        _parse_pipe_list(s.lunch_dining_halls),
                "lunch_will_go_dorm":        bool(s.lunch_will_go_dorm),
                "lunch_duration_min":        int(s.lunch_duration_min),
                "lunch_avanti_eligible":     bool(s.lunch_avanti_eligible),
                "lunch_yme_eligible":        bool(s.lunch_yme_eligible),
                "home_return_threshold_min": int(s.home_return_threshold_min),
                "library_use_rate":          float(s.library_use_rate),
                "library_destinations":      _parse_pipe_list(s.library_destinations),
                "eats_dinner_on_campus":     bool(s.eats_dinner_on_campus),
                "dinner_duration_min":       int(s.dinner_duration_min),
                "gym_days_per_week":         int(s.gym_days_per_week),
                "gym_destination":           str(s.gym_destination) if isinstance(s.gym_destination, str) else "",
                "gym_duration_min":          int(s.gym_duration_min),
            }

        # Add to big agents list
        agents.append(AgentData(
            student_id=s.id,
            year=int(s.year),
            school=s.school,
            mode=s.mode,
            speed=float(s.speed),
            dorm_name=dorm_name,
            dorm_lat=dorm_lat,
            dorm_lon=dorm_lon,
            meetings=my_meetings,
            **behavior_kwargs,
        ))

    # Safety
    if missing_dorm:
        print(f"  !! {missing_dorm} students have unresolved dorm - skipped")
    print(f"  Built {len(agents)} agents")
    print(f"  Mean meetings per agent: {sum(len(a.meetings) for a in agents)/len(agents):.1f}")

    return agents


if __name__ == "__main__":
    from collections import Counter

    # Check data from one agent
    agents = load_agents()
    print(f"\n--- Sample agent ---")
    a = agents[0]
    print(f"Student {a.student_id}: year {a.year}, {a.school}, lives at {a.dorm_name}")
    print(f"  {len(a.meetings)} meetings:")
    for m in a.meetings[:5]:
        h, mn = m.start_sec // 3600, (m.start_sec % 3600) // 60
        print(f"    {m.day:9s} {h:02d}:{mn:02d}  {m.subject} {m.course_code} ({m.component}) @ {m.building_name}")

    # Check per-day num meetings 
    day_totals = Counter()
    for a in agents:
        for m in a.meetings:
            day_totals[m.day] += 1
    print("\n=== Total day-instances by weekday ===")
    for d in ["Monday","Tuesday","Wednesday","Thursday","Friday"]:
        print(f"  {d:9s}: {day_totals[d]:5d}")

    # Check that anchor classes/lecs and linked sections both there
    anchor_count  = sum(1 for a in agents for m in a.meetings if m.is_anchor)
    linked_count  = sum(1 for a in agents for m in a.meetings if not m.is_anchor)
    print(f"\nTotal anchors:        {anchor_count}")
    print(f"Total linked (DIS):   {linked_count}")