# AGENT CLASS FOR MULI-AGENT SIMULATION
# 
# Holds the state for one student thorugh a simulated day, from AgentData 
# (sim/load_data.py) and graph + path cache (sim/runner.py)

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from sim.load_data import Meeting
rng = np.random.default_rng(42)

# home/class -> next class trip that needs to be executed
@dataclass
class TripPlan:
    target_arrival_sec: int  # when the agent needs to be at destination
    dest_node: int  # OSMnx node id
    section_id: str | None  # for "going home" = None

# One student
# State machine:
#     "home" - at dorm, waiting for next class
#     "moving" - walking/biking along a path to next class/home  
#     "in_class" - at a class destination, sitting through lecture
#     "done" - last class of the day done, returned home
class Agent:
    __slots__ = ("student_id", "speed", "buffer_sec", "current_node", "path", 
                 "path_progress", "status", "trips", "trip_idx", 
                 "current_meeting_end_sec", "_G", "_path_cache", "_edge_lengths")

    def __init__(self, student_id: str, home_node: int, speed: float, trips: list[TripPlan], G, path_cache, edge_lengths):
        self.student_id = student_id
        self.current_node = home_node
        self.speed = speed

        # Buffer time before class to leave dorm
        self.buffer_sec = max(30.0, float(rng.normal(180, 60)))

        self.path: list[int] = []
        self.path_progress: float = 0.0
        self.status: str = "home"

        self.trips = trips  # list of TripPlan, sorted by time
        self.trip_idx = 0
        self.current_meeting_end_sec: int | None = None

        # grab cached info from g
        self._G = G
        self._path_cache = path_cache
        self._edge_lengths = edge_lengths

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

    # Get cached path from node to dst, return [src] if no path
    def _get_path(self, src: int, dst: int) -> list[int]:
        return self._path_cache.get((src, dst), [src])

    def _estimate_travel_sec(self, dst: int) -> float:
        path = self._get_path(self.current_node, dst)
        if len(path) < 2:
            return 0.0
        total = sum(self._edge_lengths.get((path[i], path[i + 1]), 50.0)
                    for i in range(len(path) - 1))
        return total / max(self.speed, 0.1)

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
                # Already at dest = back-to-back classes in same building, go straight to in_class.
                if self.current_node == trip.dest_node:
                    self.status = "in_class"
                    self.current_meeting_end_sec = self._end_for_current_trip()
                    return

                path = self._get_path(self.current_node, trip.dest_node)
                if len(path) >= 2:
                    self.path = path
                    self.path_progress = 0.0
                    self.status = "moving"
                else:
                    # No cached path - graph disconnect. Snap so we don't sit at home labeled in_class.
                    print(f"[WARN] no path {self.current_node} -> {trip.dest_node} "
                          f"for {self.student_id}; snapping")
                    self.current_node = trip.dest_node
                    self.status = "in_class"
                    self.current_meeting_end_sec = self._end_for_current_trip()
            return

        # State: moving - advance along path
        if self.status == "moving":
            self.path_progress += self.speed * dt
            
            # length greater than two, move
            while len(self.path) >= 2 and self.path_progress >= \
                    self._edge_lengths.get((self.path[0], self.path[1]), 50.0):
                length = self._edge_lengths.get((self.path[0], self.path[1]), 50.0)
                self.path_progress -= length
                self.path.pop(0)
                self.current_node = self.path[0]

            # length less than two, arrived at dest, either done or in_class as of now
            if len(self.path) < 2:
                self.path_progress = 0.0
                current_trip = self.trips[self.trip_idx]

                if current_trip.section_id is None:
                    self.status = "done"
                    self.current_meeting_end_sec = None
                else:
                    self.status = "in_class"
                    self.current_meeting_end_sec = self._end_for_current_trip()

            return

        # State: in_class - wait for class to end, then prep for next trip
        if self.status == "in_class":
            if self.current_meeting_end_sec is not None and t >= self.current_meeting_end_sec:
                # Class is over; move to next trip
                self.trip_idx += 1
                self.current_meeting_end_sec = None
                self.status = "between"
            return

        # status == "done": no-op

    # Helper to know what time class ends for current trip, use to transition in_class -> between or done
    def _end_for_current_trip(self) -> int | None:
        if self.trip_idx < len(self.trips):
            t = self.trips[self.trip_idx]
            return getattr(t, "meeting_end_sec", None)
        
        return None