# AGENT CLASS FOR MULI-AGENT SIMULATION
# 
# Holds the state for one student thorugh a simulated day, from AgentData 
# (sim/load_data.py) and graph + path cache (sim/runner.py)

from __future__ import annotations
from dataclasses import dataclass
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import behavior_params as bp

rng = np.random.default_rng(42)

# One destination the agent needs to reach and stay at for some duration
# (coffee, lunch, home_stop, go_home). All trips have a target arrival time,
# a destination, a stay duration, and a purpose tag for diagnostics/eval
@dataclass
class TripPlan:
    target_arrival_sec: int  # when the agent needs to be at destination
    dest_node: int  # OSMnx node id
    section_id: str | None  # original class section_id; None for non-class trips
    purpose: str = "class"  # class | coffee | lunch | home_stop | go_home
    duration_sec: int = 0  # how long agent stays at dest; end_sec = target + duration

# One student
# State machine:
#     "home" - at dorm, waiting for next class
#     "moving" - walking/biking along a path to next class/home  
#     "in_class" - at a class destination, sitting through lecture
#     "done" - last class of the day done, returned home
class Agent:
    __slots__ = ("student_id", "speed", "mode", "buffer_sec", "current_node", "path",
                 "path_progress", "status", "trips", "trip_idx",
                 "current_dest_end_sec", "_G", "_path_cache",
                 "_edge_lengths", "_edge_walk_ok", "_edge_bike_ok",
                 "n_skipped_walks")

    def __init__(self, student_id: str, home_node: int, speed: float, mode: str,
                 trips: list[TripPlan], G,
                 path_cache_walk: dict, path_cache_bike: dict,
                 edge_lengths: dict, edge_walk_ok: dict, edge_bike_ok: dict):
        self.student_id = student_id
        self.current_node = home_node
        self.speed = speed
        self.mode = mode  # "walk" | "bike" | "electric"

        # Buffer time before class to leave dorm
        self.buffer_sec = max(30.0, float(rng.normal(180, 60)))

        self.path: list[int] = []
        self.path_progress: float = 0.0
        self.status: str = "home"

        self.trips = trips  # list of TripPlan, sorted by time
        self.trip_idx = 0
        self.current_dest_end_sec: int | None = None

        # grab cached info from g
        self._G = G
        # Bikers + e-bikes route on the bike cache (composed graph with walk-only edges penalized); walkers on the walk-only cache
        self._path_cache = path_cache_bike if mode in ("bike", "electric") else path_cache_walk
        self._edge_lengths = edge_lengths
        self._edge_walk_ok = edge_walk_ok
        self._edge_bike_ok = edge_bike_ok

        # Diagnostic: count trips where home/dest collide on a single graph node so the agent was forced to skip the walk entirely
        self.n_skipped_walks = 0

    # ----------- helpers --------------

    # Get lat long for current position
    def position(self) -> tuple[float, float]:
        if self.status == "moving" and len(self.path) >= 2:
            u, v = self.path[0], self.path[1]
            length = self._edge_lengths.get((u, v), 50.0)
            frac = self.path_progress / length if length > 0 else 0.0

            lat_u, lon_u = self._G.nodes[u]['y'], self._G.nodes[u]['x']
            lat_v, lon_v = self._G.nodes[v]['y'], self._G.nodes[v]['x']

            return (lat_u + frac * (lat_v - lat_u), lon_u + frac * (lon_v - lon_u))

        n = self.current_node
        return (self._G.nodes[n]['y'], self._G.nodes[n]['x'])

    # (u, v) for the edge being traversed, else (None, None). Used by trajectory recorder.
    def current_edge(self) -> tuple[int | None, int | None]:
        if self.status == "moving" and len(self.path) >= 2:
            return (self.path[0], self.path[1])
        return (None, None)

    # Purpose of the current trip "class"/"coffee"/"lunch"/"home_stop"/"go_home"
    def current_purpose(self) -> str:
        if 0 <= self.trip_idx < len(self.trips):
            return self.trips[self.trip_idx].purpose
        return ""

    # Get cached path node to dst return [src] if no path
    def _get_path(self, src: int, dst: int) -> list[int]:
        cached = self._path_cache.get((src, dst))
        if cached is None:
            return [src]
        return list(cached)

    # Effective traversal speed on edge (u, v) for this agent
    # biker on walk-only treated as dismount -> BIKER_DISMOUNT_SPEED_MPS
    def _edge_speed(self, u: int, v: int) -> float:
        if self.mode in ("bike", "electric") and not self._edge_bike_ok.get((u, v), True):
            return bp.BIKER_DISMOUNT_SPEED_MPS
        return self.speed

    def _estimate_travel_sec(self, dst: int) -> float:
        path = self._get_path(self.current_node, dst)
        if len(path) < 2:
            return 0.0
        total_sec = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            length = self._edge_lengths.get((u, v), 50.0)
            total_sec += length / max(self._edge_speed(u, v), 0.1)
        return total_sec

    # ---------------- main api ---------------------

    def update(self, t: int, dt: int) -> None:
        # State: home - check if it's time to leave
        if self.status in ("home", "between"):
            if self.trip_idx >= len(self.trips):
                self.status = "done"
                return
            
            trip = self.trips[self.trip_idx]
            travel = self._estimate_travel_sec(trip.dest_node)
            depart_at = trip.target_arrival_sec - self.buffer_sec - travel

            if t >= depart_at:

                if self.current_node == trip.dest_node and self.status == "between":
                    self.status = "in_class"
                    self.current_dest_end_sec = self._end_for_current_trip()
                    return

                path = self._get_path(self.current_node, trip.dest_node)
                if len(path) >= 2:
                    self.path = path
                    self.path_progress = 0.0
                    self.status = "moving"
                elif self.current_node == trip.dest_node:

                    self.n_skipped_walks += 1
                    self.status = "in_class"
                    self.current_dest_end_sec = self._end_for_current_trip()
                else:
                    # No cached path
                    # Snap so we actually move
                    print(f"[WARN] no path {self.current_node} -> {trip.dest_node} "
                          f"for {self.student_id}; snapping")
                    
                    self.current_node = trip.dest_node
                    self.status = "in_class"
                    self.current_dest_end_sec = self._end_for_current_trip()
            return

        # State: moving - advance along path using per-edge speed (so bikers -> dismount speed when walk-only segments)
        if self.status == "moving":
            if len(self.path) >= 2:
                u, v = self.path[0], self.path[1]
                self.path_progress += self._edge_speed(u, v) * dt

            while len(self.path) >= 2 and self.path_progress >= \
                    self._edge_lengths.get((self.path[0], self.path[1]), 50.0):
                
                length = self._edge_lengths.get((self.path[0], self.path[1]), 50.0)
                self.path_progress -= length
                self.path.pop(0)
                self.current_node = self.path[0]

            # Path drained
            # agent arrived. go_home -> done; everything else
            # (class / coffee / lunch / home_stop) -> sit at dest for duration
            if len(self.path) < 2:
                self.path_progress = 0.0
                current_trip = self.trips[self.trip_idx]

                if current_trip.purpose == "go_home":
                    self.status = "done"
                    self.current_dest_end_sec = None
                else:
                    self.status = "in_class"
                    self.current_dest_end_sec = self._end_for_current_trip()

            return

        # State: in_class - sit at destination until duration elapses, then move on
        # Covers classes AND behavior trips (coffee/lunch/home_stop)
        if self.status == "in_class":
            if self.current_dest_end_sec is not None and t >= self.current_dest_end_sec:
                self.trip_idx += 1
                self.current_dest_end_sec = None
                self.status = "between"
            return

        # status == "done": no-op

    # Absolute time the agent should leave the current destination
    def _end_for_current_trip(self) -> int | None:
        if self.trip_idx < len(self.trips):
            t = self.trips[self.trip_idx]
            return t.target_arrival_sec + t.duration_sec
        return None