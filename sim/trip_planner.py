# TRIP PLANNER

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim.agent import TripPlan
from sim.load_data import AgentData, Meeting
from sim.map_buildings import ALL_LOCATIONS
from pipeline import behavior_params as bp

WEEKDAY_INDEX = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}

WALK_SPEED_PLANNER_MPS = 1.5  # for travel-time estimates inside this module
SIM_START_SEC = 6 * 3600
SIM_END_SEC = 22 * 3600


# ------ Geometry / travel estimates -------

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def walk_min(meters: float) -> float:
    return meters / WALK_SPEED_PLANNER_MPS / 60.0


def loc_of(key: str) -> tuple[float, float] | None:
    entry = ALL_LOCATIONS.get(key)
    if entry is None:
        return None
    return (entry[1], entry[2])


def travel_min_between(loc_a: tuple[float, float] | None,
                       loc_b: tuple[float, float] | None) -> float:
    if loc_a is None or loc_b is None:
        return 0.0
    return walk_min(haversine_m(loc_a[0], loc_a[1], loc_b[0], loc_b[1]))


# ---------- RNG ------------
def rng_for_agent_day(student_id, day: str) -> np.random.Generator:
    # Stable, independent across (agent, day) pairs.
    sid_int = int(student_id) if str(student_id).isdigit() else hash(str(student_id)) & 0xFFFFFFFF
    day_int = WEEKDAY_INDEX.get(day, 5)
    return np.random.default_rng([bp.BEHAVIOR_RNG_SEED, sid_int, day_int])


# ----------- Coffee decisions -----------

def _make_coffee_trip(agent: AgentData, target_arrival_sec: int, duration_sec: int,
                      dest_node: int) -> TripPlan:
    return TripPlan(
        target_arrival_sec=target_arrival_sec,
        dest_node=dest_node,
        section_id=None,
        purpose="coffee",
        duration_sec=duration_sec,
    )


def decide_coffee_trip(agent: AgentData, class_meetings: list[Meeting], G, cached_nearest_node, rng: np.random.Generator) -> TripPlan | None:
    if not agent.is_coffee_drinker or not agent.coffee_destination:
        return None

    coffee_loc = loc_of(agent.coffee_destination)
    if coffee_loc is None:
        return None
    coffee_node = cached_nearest_node(G, coffee_loc[1], coffee_loc[0])

    dorm_loc = (agent.dorm_lat, agent.dorm_lon)
    dorm_to_coffee_min = travel_min_between(dorm_loc, coffee_loc)

    grab_dur_sec = int(round(max(2, rng.normal(bp.COFFEE_GRAB_DURATION_MIN_MEAN, bp.COFFEE_GRAB_DURATION_MIN_STD)))) * 60

    # No class today: morning grab-and-go at ~08:30
    if not class_meetings:
        return _make_coffee_trip(agent, target_arrival_sec=8 * 3600 + 30 * 60,
                                  duration_sec=grab_dur_sec, dest_node=coffee_node)

    first_class = class_meetings[0]
    first_loc = (first_class.lat, first_class.lon)
    first_start_hr = first_class.start_sec / 3600.0
    coffee_to_class_min = travel_min_between(coffee_loc, first_loc)
    class_buffer_min = 5

    if agent.is_early_riser:
        if first_start_hr >= bp.COFFEE_EARLY_RISER_SIT_THRESHOLD_HR:
            # Sit n sip until class
            need_to_leave_sec = first_class.start_sec - int((coffee_to_class_min + class_buffer_min) * 60)
            target_arrival_sec = max(SIM_START_SEC, need_to_leave_sec - bp.COFFEE_SIT_DURATION_MIN_DEFAULT * 60)
            duration_sec = need_to_leave_sec - target_arrival_sec
            
            if duration_sec < 5 * 60:
                # Not enough sit time
                target_arrival_sec = need_to_leave_sec - grab_dur_sec
                duration_sec = grab_dur_sec

            return _make_coffee_trip(agent, target_arrival_sec, duration_sec, coffee_node)
        else:
            # Early class: try a quick grab-and-go skip if can't fit.
            need_to_leave_sec = first_class.start_sec - int((coffee_to_class_min + class_buffer_min) * 60)
            target_arrival_sec = need_to_leave_sec - grab_dur_sec
            dorm_leave_sec = target_arrival_sec - int(dorm_to_coffee_min * 60)
            if dorm_leave_sec < SIM_START_SEC:
                return None
            return _make_coffee_trip(agent, target_arrival_sec, grab_dur_sec, coffee_node)

    # Not early riser
    if first_start_hr < bp.COFFEE_LATE_RISER_SKIP_THRESHOLD_HR:
        # Skip morning try afternoon
        return _afternoon_coffee_trip(agent, class_meetings, coffee_node, coffee_loc,
                                       grab_dur_sec, rng)
    else:
        # Late riser, late enough class
        need_to_leave_sec = first_class.start_sec - int((coffee_to_class_min + class_buffer_min) * 60)
        target_arrival_sec = need_to_leave_sec - grab_dur_sec
        if target_arrival_sec < SIM_START_SEC:
            return None
        return _make_coffee_trip(agent, target_arrival_sec, grab_dur_sec, coffee_node)


def _afternoon_coffee_trip(agent: AgentData, class_meetings: list[Meeting],
                            coffee_node: int, coffee_loc: tuple[float, float],
                            grab_dur_sec: int, rng: np.random.Generator) -> TripPlan | None:
    win_start, win_end = bp.COFFEE_AFTERNOON_WINDOW_SEC

    for i in range(len(class_meetings)):
        prev = class_meetings[i]
        next_class = class_meetings[i + 1] if i + 1 < len(class_meetings) else None
        gap_start = prev.end_sec
        gap_end = next_class.start_sec if next_class else SIM_END_SEC

        # Restrict to overlap with afternoon window
        gap_start = max(gap_start, win_start)
        gap_end = min(gap_end, win_end)
        if gap_end - gap_start < grab_dur_sec + 120:
            continue

        prev_loc = (prev.lat, prev.lon)
        next_loc = (next_class.lat, next_class.lon) if next_class else (agent.dorm_lat, agent.dorm_lon)
        prev_to_coffee_min = travel_min_between(prev_loc, coffee_loc)
        coffee_to_next_min = travel_min_between(coffee_loc, next_loc)

        # Must fit: travel + grab + travel back, + 3-min buffer before next class
        needed_sec = int((prev_to_coffee_min + coffee_to_next_min) * 60) + grab_dur_sec + 3 * 60
        if needed_sec > (gap_end - gap_start):
            continue

        target_arrival_sec = gap_start + int(prev_to_coffee_min * 60)
        return _make_coffee_trip(agent, target_arrival_sec, grab_dur_sec, coffee_node)
    return None


# -------- Lunch decisions --------
def _adjusted_lunch_rate(agent: AgentData, class_meetings: list[Meeting]) -> float:
    rate = agent.eats_lunch_on_campus_base

    midday = [m for m in class_meetings if 10 * 3600 <= m.start_sec < 15 * 3600]
    if len(midday) >= bp.LUNCH_TIGHT_DAY_MIN_CLASSES:
        gaps_min = [(midday[i + 1].start_sec - midday[i].end_sec) / 60
                    for i in range(len(midday) - 1)]
        if gaps_min and max(gaps_min) <= bp.LUNCH_TIGHT_DAY_MAX_GAP_MIN:
            rate = min(rate * bp.LUNCH_TIGHT_DAY_MULTIPLIER, bp.LUNCH_ADJUSTED_RATE_CAP)
            return rate

    last_end_sec = max((m.end_sec for m in class_meetings), default=0)
    if len(class_meetings) <= 1 or last_end_sec < 11 * 3600:
        rate = rate * bp.LUNCH_LIGHT_DAY_MULTIPLIER

    return rate

def _lunch_candidates(agent: AgentData) -> list[tuple[str, str, float]]:
    out: list[tuple[str, str, float]] = []

    for e in agent.lunch_eateries:
        out.append((e, "eatery", bp.LUNCH_BASE_TYPE_WEIGHTS["eatery"]))

    halls = list(agent.lunch_dining_halls)
    if agent.lunch_avanti_eligible:
        halls.append(bp.AVANTI_DINING_HALL)
    if agent.lunch_yme_eligible:
        halls.append(bp.YME_DINING_HALL)
    for h in halls:
        out.append((h, "dining_hall", bp.LUNCH_BASE_TYPE_WEIGHTS["dining_hall"]))

    if agent.lunch_will_go_dorm:
        out.append((agent.dorm_name, "dorm", bp.LUNCH_BASE_TYPE_WEIGHTS["dorm"]))

    return out


# Pick lunch dest weighted by base type + distance from `from_loc`
def _choose_lunch_destination(agent: AgentData, from_loc: tuple[float, float],
                               rng: np.random.Generator) -> str | None:
    candidates = _lunch_candidates(agent)
    if not candidates:
        return None

    weights = []
    for dest, _, base_w in candidates:
        dest_loc = loc_of(dest) if dest != agent.dorm_name else (agent.dorm_lat, agent.dorm_lon)
        if dest_loc is None:
            weights.append(0.0)
            continue
        travel = travel_min_between(from_loc, dest_loc)
        weights.append(base_w * math.exp(-travel / bp.LUNCH_DISTANCE_DECAY_SCALE_MIN))

    weights = np.array(weights, dtype=float)
    if weights.sum() == 0:
        return None
    probs = weights / weights.sum()
    idx = rng.choice(len(candidates), p=probs)
    return candidates[idx][0]


# -------- Per-gap decision: lunch vs home_stop vs nothing --------

def decide_gap_trip(agent: AgentData, prev: Meeting, next_class: Meeting,
                    class_meetings: list[Meeting], has_lunch_already: bool,
                    G, cached_nearest_node, rng: np.random.Generator) -> TripPlan | None:
    gap_start = prev.end_sec
    gap_end = next_class.start_sec
    gap_min = (gap_end - gap_start) / 60.0
    prev_loc = (prev.lat, prev.lon)
    next_loc = (next_class.lat, next_class.lon)
    dorm_loc = (agent.dorm_lat, agent.dorm_lon)

    # --- Lunch eligibility ---
    lunch_win_start, lunch_win_end = bp.LUNCH_WINDOW_SEC
    gap_intersects_lunch = (gap_start < lunch_win_end and gap_end > lunch_win_start)

    lunch_rate = _adjusted_lunch_rate(agent, class_meetings)
    lunch_rolled = rng.random() < lunch_rate
    lunch_eligible = (gap_intersects_lunch and lunch_rolled and not has_lunch_already)

    # --- Home return eligibility ---
    travel_home_min = travel_min_between(prev_loc, dorm_loc)
    travel_back_min = travel_min_between(dorm_loc, next_loc)
    home_stay_min = gap_min - travel_home_min - travel_back_min - 5  # 5-min buffer for next class
    home_eligible = (gap_min >= agent.home_return_threshold_min
                     and home_stay_min >= bp.HOME_RETURN_MIN_STAY_MIN)

    # --- Resolve ---
    if lunch_eligible and home_eligible:
        p_home = max(0.1, min(0.9, 1 - travel_home_min / bp.HOME_RETURN_TRAVEL_DECAY_SCALE_MIN))
        if rng.random() < p_home:
            return _make_home_stop(agent, gap_start, gap_end, travel_home_min,
                                    home_stay_min, G, cached_nearest_node)
        return _make_lunch_trip(agent, gap_start, prev_loc, next_loc, gap_end,
                                G, cached_nearest_node, rng)

    if lunch_eligible:
        return _make_lunch_trip(agent, gap_start, prev_loc, next_loc, gap_end,
                                G, cached_nearest_node, rng)
    if home_eligible:
        return _make_home_stop(agent, gap_start, gap_end, travel_home_min,
                                home_stay_min, G, cached_nearest_node)
    return None


def _make_lunch_trip(agent: AgentData, gap_start: int,
                     prev_loc: tuple[float, float], next_loc: tuple[float, float],
                     gap_end: int, G, cached_nearest_node,
                     rng: np.random.Generator) -> TripPlan | None:
    dest_key = _choose_lunch_destination(agent, prev_loc, rng)
    if dest_key is None:
        return None
    dest_loc = loc_of(dest_key) if dest_key != agent.dorm_name else (agent.dorm_lat, agent.dorm_lon)
    if dest_loc is None:
        return None
    dest_node = cached_nearest_node(G, dest_loc[1], dest_loc[0])

    travel_to_min = travel_min_between(prev_loc, dest_loc)
    travel_back_min = travel_min_between(dest_loc, next_loc)
    duration_min = agent.lunch_duration_min
    needed_min = travel_to_min + duration_min + travel_back_min + 5
    if needed_min * 60 > (gap_end - gap_start):
        return None  # skip lunch no fit

    target_arrival_sec = gap_start + int(travel_to_min * 60)
    return TripPlan(
        target_arrival_sec=target_arrival_sec,
        dest_node=dest_node,
        section_id=None,
        purpose="lunch",
        duration_sec=duration_min * 60,
    )


def _make_home_stop(agent: AgentData, gap_start: int, gap_end: int,
                    travel_home_min: float, home_stay_min: float,
                    G, cached_nearest_node) -> TripPlan:
    home_node = cached_nearest_node(G, agent.dorm_lon, agent.dorm_lat)
    target_arrival_sec = gap_start + int(travel_home_min * 60)
    return TripPlan(
        target_arrival_sec=target_arrival_sec,
        dest_node=home_node,
        section_id=None,
        purpose="home_stop",
        duration_sec=int(home_stay_min * 60),
    )


# ------------ Library ------------

def _library_eligible_destinations(agent: AgentData,
                                    from_loc: tuple[float, float]) -> list[tuple[str, float]]:
    """Return (dest_key, weight) for the agent's library prefs, distance-decayed."""
    out: list[tuple[str, float]] = []
    for lib in agent.library_destinations:
        loc = loc_of(lib)
        if loc is None:
            continue
        travel = travel_min_between(from_loc, loc)
        weight = math.exp(-travel / bp.LUNCH_DISTANCE_DECAY_SCALE_MIN)
        out.append((lib, weight))
    return out


def decide_library_trip(agent: AgentData, gap_start: int, gap_end: int,
                         prev_loc: tuple[float, float], next_loc: tuple[float, float],
                         G, cached_nearest_node, rng: np.random.Generator) -> TripPlan | None:
    gap_min = (gap_end - gap_start) / 60.0
    if gap_min < bp.LIBRARY_MIN_GAP_MIN:
        return None
    if rng.random() >= agent.library_use_rate:
        return None

    candidates = _library_eligible_destinations(agent, prev_loc)
    if not candidates:
        return None

    weights = np.array([w for _, w in candidates], dtype=float)
    if weights.sum() == 0:
        return None
    probs = weights / weights.sum()
    dest = candidates[rng.choice(len(candidates), p=probs)][0]
    dest_loc = loc_of(dest)
    if dest_loc is None:
        return None
    dest_node = cached_nearest_node(G, dest_loc[1], dest_loc[0])

    travel_to_min = travel_min_between(prev_loc, dest_loc)
    travel_back_min = travel_min_between(dest_loc, next_loc)
    duration_min = min(bp.LIBRARY_DURATION_CAP_MIN,
                        gap_min - travel_to_min - travel_back_min - 5)
    if duration_min < 15:  # not worth library run
        return None

    target_arrival_sec = gap_start + int(travel_to_min * 60)
    return TripPlan(
        target_arrival_sec=target_arrival_sec,
        dest_node=dest_node,
        section_id=None,
        purpose="library",
        duration_sec=int(duration_min * 60),
    )


# ------------ Dinner ------------

def _choose_dinner_destination(agent: AgentData, from_loc: tuple[float, float],
                                rng: np.random.Generator) -> str | None:
    candidates: list[tuple[str, str, float]] = []
    for e in agent.lunch_eateries:
        candidates.append((e, "eatery", bp.DINNER_BASE_TYPE_WEIGHTS["eatery"]))
    halls = list(agent.lunch_dining_halls)
    if agent.lunch_avanti_eligible:
        halls.append(bp.AVANTI_DINING_HALL)
    if agent.lunch_yme_eligible:
        halls.append(bp.YME_DINING_HALL)
    for h in halls:
        candidates.append((h, "dining_hall", bp.DINNER_BASE_TYPE_WEIGHTS["dining_hall"]))
    if agent.lunch_will_go_dorm:
        candidates.append((agent.dorm_name, "dorm", bp.DINNER_BASE_TYPE_WEIGHTS["dorm"]))
    if not candidates:
        return None

    weights = []
    for dest, _, base_w in candidates:
        if dest == agent.dorm_name:
            dest_loc = (agent.dorm_lat, agent.dorm_lon)
        else:
            dest_loc = loc_of(dest)
        if dest_loc is None:
            weights.append(0.0)
            continue
        travel = travel_min_between(from_loc, dest_loc)
        weights.append(base_w * math.exp(-travel / bp.LUNCH_DISTANCE_DECAY_SCALE_MIN))

    weights = np.array(weights, dtype=float)
    if weights.sum() == 0:
        return None
    probs = weights / weights.sum()
    return candidates[rng.choice(len(candidates), p=probs)][0]


def decide_dinner_trip(agent: AgentData, after_last_class_sec: int,
                        last_class_loc: tuple[float, float],
                        G, cached_nearest_node, rng: np.random.Generator) -> TripPlan | None:
    
    if not agent.eats_dinner_on_campus:
        return None

    win_start, win_end = bp.DINNER_WINDOW_SEC
    earliest = max(after_last_class_sec, win_start)
    if earliest >= win_end:
        return None  # no time left in dinner window

    dest = _choose_dinner_destination(agent, last_class_loc, rng)
    if dest is None:
        return None

    if dest == agent.dorm_name:
        dest_loc = (agent.dorm_lat, agent.dorm_lon)
    else:
        dest_loc = loc_of(dest)
    if dest_loc is None:
        return None
    dest_node = cached_nearest_node(G, dest_loc[1], dest_loc[0])

    travel_min = travel_min_between(last_class_loc, dest_loc)
    duration_sec = agent.dinner_duration_min * 60
    target_arrival_sec = earliest + int(travel_min * 60)
    if target_arrival_sec + duration_sec > win_end:
        return None  # would push past dinner window

    return TripPlan(
        target_arrival_sec=target_arrival_sec,
        dest_node=dest_node,
        section_id=None,
        purpose="dinner",
        duration_sec=duration_sec,
    )


# ------------ Gym ------------

def _sample_gym_target_hour(rng: np.random.Generator) -> int:
    hours = list(bp.GYM_START_HOUR_WEIGHTS.keys())
    weights = np.array(list(bp.GYM_START_HOUR_WEIGHTS.values()), dtype=float)
    probs = weights / weights.sum()
    return int(rng.choice(hours, p=probs))


def is_gym_today(agent: AgentData, rng: np.random.Generator) -> bool:
    if agent.gym_days_per_week <= 0:
        return False
    return bool(rng.uniform(0, 7) < agent.gym_days_per_week)


def _try_fit_gym_in_gap(agent: AgentData, gap_start: int, gap_end: int,
                         entry_loc: tuple[float, float], exit_loc: tuple[float, float],
                         target_hour: int) -> tuple[int, int] | None:
    """If gym fits in this gap with given entry/exit locations, return
    (target_arrival_sec, duration_sec). Otherwise None."""
    gym_loc = loc_of(agent.gym_destination)
    if gym_loc is None:
        return None
    travel_in = travel_min_between(entry_loc, gym_loc)
    travel_out = travel_min_between(gym_loc, exit_loc)
    duration_min = agent.gym_duration_min
    needed_sec = int((travel_in + travel_out) * 60) + duration_min * 60 + 5 * 60  # 5-min slack

    if gap_end - gap_start < needed_sec:
        return None

    desired_arrival = target_hour * 3600
    earliest_arrival = gap_start + int(travel_in * 60)
    latest_arrival = gap_end - duration_min * 60 - int(travel_out * 60) - 5 * 60
    if latest_arrival < earliest_arrival:
        return None
    target_arrival_sec = max(earliest_arrival, min(latest_arrival, desired_arrival))
    return target_arrival_sec, duration_min * 60


def decide_gym_placement(agent: AgentData, day_meetings: list[Meeting],
                          target_hour: int) -> tuple[int, TripPlan, str] | None:
    """Returns (gap_idx, gym_trip, slot) where slot is 'intra' (between classes)
    or 'after_last' (post-last-class). gap_idx for intra is the index in
    day_meetings (gap between day_meetings[i] and day_meetings[i+1]); for
    'after_last' it's len(day_meetings)-1. Returns None if no gap fits.
    """
    gym_node_loc = loc_of(agent.gym_destination)
    if gym_node_loc is None:
        return None

    candidates: list[tuple[int, int, tuple[float, float], tuple[float, float], str, int]] = []
    if day_meetings:
        first = day_meetings[0]
        candidates.append((
            SIM_START_SEC, first.start_sec,
            (agent.dorm_lat, agent.dorm_lon), (first.lat, first.lon),
            "pre_first", -1,
        ))

        for i in range(len(day_meetings) - 1):
            prev, nxt = day_meetings[i], day_meetings[i + 1]
            candidates.append((
                prev.end_sec, nxt.start_sec,
                (prev.lat, prev.lon), (nxt.lat, nxt.lon),
                "intra", i,
            ))

        last = day_meetings[-1]
        candidates.append((
            last.end_sec, SIM_END_SEC,
            (last.lat, last.lon), (agent.dorm_lat, agent.dorm_lon),
            "after_last", len(day_meetings) - 1,
        ))
    else:
        candidates.append((
            SIM_START_SEC, SIM_END_SEC,
            (agent.dorm_lat, agent.dorm_lon), (agent.dorm_lat, agent.dorm_lon),
            "after_last", -1,
        ))

    target_sec = target_hour * 3600

    def gap_distance(c):
        gs, ge = c[0], c[1]
        if gs <= target_sec <= ge:
            return 0
        return min(abs(gs - target_sec), abs(ge - target_sec))

    candidates_sorted = sorted(candidates, key=gap_distance)

    for gs, ge, entry, exit_, slot, gidx in candidates_sorted:
        gym_node = None
        fit = _try_fit_gym_in_gap(agent, gs, ge, entry, exit_, target_hour)
        if fit is None:
            continue
        target_arrival_sec, duration_sec = fit
        gym_loc = loc_of(agent.gym_destination)

        return gidx, TripPlan(
            target_arrival_sec=target_arrival_sec,
            dest_node=-1,
            section_id=None,
            purpose="gym",
            duration_sec=duration_sec,
        ), slot
    return None


# ------------ Main trip build --------------
def build_trips_for_day(agent: AgentData, day: str, G, cached_nearest_node) -> list[TripPlan]:
    day_meetings = sorted([m for m in agent.meetings if m.day == day], key=lambda m: m.start_sec)
    if not day_meetings:
        return []

    rng = rng_for_agent_day(agent.student_id, day)

    # ---- 1. Coffee ----
    coffee = decide_coffee_trip(agent, day_meetings, G, cached_nearest_node, rng)

    # ---- 2. Class trips ----
    class_trips: list[TripPlan] = []
    for m in day_meetings:
        dest_node = cached_nearest_node(G, m.lon, m.lat)
        class_trips.append(TripPlan(
            target_arrival_sec=m.start_sec,
            dest_node=dest_node,
            section_id=m.section_id,
            purpose="class",
            duration_sec=m.end_sec - m.start_sec,
        ))

    # ---- 3. Gym ----
    gym_trip: TripPlan | None = None
    gym_intra_gap_idx: int | None = None
    gym_slot: str | None = None
    if is_gym_today(agent, rng):
        target_hour = _sample_gym_target_hour(rng)
        placement = decide_gym_placement(agent, day_meetings, target_hour)
        if placement is not None:
            gidx, gtrip, slot = placement

            gym_loc = loc_of(agent.gym_destination)
            if gym_loc is not None:
                gtrip.dest_node = cached_nearest_node(G, gym_loc[1], gym_loc[0])
                gym_trip = gtrip
                gym_slot = slot

                if slot == "intra":
                    gym_intra_gap_idx = gidx

    # ---- 4. Per-intra-class-gap: lunch | home_stop | library | (none) ----
    # Gap claimed by gym is skipped.
    gap_trips: list[TripPlan] = []
    has_lunch = False
    for i in range(len(day_meetings) - 1):
        if gym_intra_gap_idx == i:
            continue  # this gap is gym's
        prev = day_meetings[i]
        nxt = day_meetings[i + 1]

        gap_trip = decide_gap_trip(agent, prev, nxt, day_meetings, has_lunch,
                                    G, cached_nearest_node, rng)
        if gap_trip is None:

            gap_trip = decide_library_trip(agent, prev.end_sec, nxt.start_sec,
                                            (prev.lat, prev.lon), (nxt.lat, nxt.lon),
                                            G, cached_nearest_node, rng)
        if gap_trip is None:
            continue
        if gap_trip.purpose == "lunch":
            has_lunch = True
        gap_trips.append(gap_trip)

    # ---- 5. Post-last-class window: dinner (optional), then go_home ----
    last = max(day_meetings, key=lambda m: m.end_sec)
    last_loc = (last.lat, last.lon)
    home_node = cached_nearest_node(G, agent.dorm_lon, agent.dorm_lat)

    after_last_sec = last.end_sec

    if gym_trip is not None and gym_slot == "after_last":
        gym_end = gym_trip.target_arrival_sec + gym_trip.duration_sec

        if gym_end > after_last_sec:
            after_last_sec = gym_end

    dinner = decide_dinner_trip(agent, after_last_sec, last_loc,
                                 G, cached_nearest_node, rng)

    if dinner is not None:
        go_home_arrival = dinner.target_arrival_sec + dinner.duration_sec + 5 * 60
    else:
        go_home_arrival = after_last_sec + 30 * 60

    go_home_arrival = min(go_home_arrival, SIM_END_SEC - 1)

    go_home = TripPlan(
        target_arrival_sec=go_home_arrival,
        dest_node=home_node,
        section_id=None,
        purpose="go_home",
        duration_sec=24 * 3600,
    )

    # ---- 6. Combine + sort ----
    all_trips: list[TripPlan] = []

    if coffee is not None:
        all_trips.append(coffee)
    all_trips.extend(class_trips)
    all_trips.extend(gap_trips)

    if gym_trip is not None:
        all_trips.append(gym_trip)

    if dinner is not None:
        all_trips.append(dinner)

    all_trips.append(go_home)
    all_trips.sort(key=lambda tp: tp.target_arrival_sec)
    
    return all_trips
