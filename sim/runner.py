# MULTI-AGENT RUNNER
#
# Usage from project root
#     python sim/runner.py                # default: 100 agents, 1 weekday
#     python sim/runner.py --n 6700 --day Monday
#
# Outputs:
#     outputs/trajectory.parquet     - sampled agent positions over time
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import OUTPUTS
from sim.load_data import AgentData, Meeting, load_agents
from sim.agent import Agent, TripPlan


# Sim params
SIM_START_SEC = 6 * 3600  # 06:00
SIM_END_SEC = 22 * 3600  # 22:00
DT_SEC = 10  # update timestep
SAMPLE_EVERY = 30 # record position every N sim seconds


@dataclass
class SimOutput:
    timestamps: list[int]
    agent_ids:  list[str]
    lats: list[float]
    lons: list[float]
    statuses: list[str]
    # (u, v) of edge being traversed, None for non-moving agents
    edge_us: list[int | None]
    edge_vs: list[int | None]

# Node Caching 
_nearest_node_cache = {}

def cached_nearest_node(G, lon, lat):
    key = (round(lat, 6), round(lon, 6))  # 6 decimal = ~10cm precision

    if key not in _nearest_node_cache:
        _nearest_node_cache[key] = ox.nearest_nodes(G, lon, lat)

    return _nearest_node_cache[key]

# Path caching 
# precomputer shortest paths btwn every pair of nodes the sim needs, cache it
# Returns:
#    path_cache:  {(src, dst): [n1, n2, ...]} for every (src, dst) pair
#    edge_lengths:  {(u, v): length} for fast O(1) edge length lookup
def build_path_cache(G, all_nodes: set[int]) -> tuple[dict, dict]:
    print(f"Precomputing shortest paths among {len(all_nodes)} unique nodes...")
    t0 = time.time()
    path_cache: dict[tuple[int, int], list[int]] = {}

    nodes_list = list(all_nodes)
    missing_pairs = 0
    for i, src in enumerate(nodes_list):
        if i % 20 == 0:
            print(f"  {i}/{len(nodes_list)}...")
        _, paths = nx.single_source_dijkstra(G, src, weight="length")
        for dst in nodes_list:
            if dst in paths:
                path_cache[(src, dst)] = paths[dst]
            elif src != dst:
                missing_pairs += 1

    print(f"  Built {len(path_cache)} cached paths in {time.time()-t0:.1f}s")
    if missing_pairs:
        print(f"  WARNING: {missing_pairs} (src,dst) pairs have no path — "
              f"graph likely has disconnected components")

    # Edge length lookup: avoid G[u][v][key]['length'] repeats
    edge_lengths: dict[tuple[int, int], float] = {}

    for u, v, data in G.edges(data=True):
        length = data.get("length", 50.0)
        # Take min if multi-edge
        if (u, v) not in edge_lengths or length < edge_lengths[(u, v)]:
            edge_lengths[(u, v)] = length

    return path_cache, edge_lengths


# Convert AgentData -> Agent with TripPlans
# Given agent's full week, get TripPlans for 'target_day' then add go home after last class
def build_trips_for_day(adata: AgentData, target_day: str, G) -> list[TripPlan]:
    day_meetings = [m for m in adata.meetings if m.day == target_day]
    day_meetings.sort(key=lambda m: m.start_sec)

    if not day_meetings:
        return []

    trips: list[TripPlan] = []
    for m in day_meetings:
        # dest_node = ox.nearest_nodes(G, m.lon, m.lat)
        dest_node = cached_nearest_node(G, m.lon, m.lat)
        tp = TripPlan(
            target_arrival_sec=m.start_sec,
            dest_node=dest_node,
            section_id=m.section_id,
        )
        # Stash end time for in_class -> ready transition
        tp.meeting_end_sec = m.end_sec
        trips.append(tp)

    # "Go home" trip after the last class
    # home_node = ox.nearest_nodes(G, adata.dorm_lon, adata.dorm_lat)
    home_node = cached_nearest_node(G, adata.dorm_lon, adata.dorm_lat)
    last = max(day_meetings, key=lambda m: m.end_sec)
    home_trip = TripPlan(
        target_arrival_sec=last.end_sec + 30 * 60,  # 30 min target
        dest_node=home_node,
        section_id=None,
    )
    home_trip.meeting_end_sec = SIM_END_SEC + 1  # never end "home"-class
    trips.append(home_trip)

    return trips


# Main sim
def run_simulation(n_agents: int = 100, target_day: str = "Monday") -> SimOutput:
    print(f"=== Loading data ===")
    all_agents_data = load_agents()

    if n_agents < len(all_agents_data):
        rng = np.random.default_rng(42)
        idx = rng.choice(len(all_agents_data), n_agents, replace=False)
        all_agents_data = [all_agents_data[i] for i in idx]

    print(f"Simulating {len(all_agents_data)} agents on {target_day}")

    print(f"\n=== Loading campus graph ===")
    t0 = time.time()
    G = ox.graph_from_place("Stanford University, California", network_type="walk")
    # Use only the largest component so every (home, class) pair has a path
    n_before = len(G.nodes)
    G = ox.truncate.largest_component(G, strongly=False)
    print(f"  Graph: {len(G.nodes)} nodes, {len(G.edges)} edges  "
          f"({time.time()-t0:.1f}s; dropped {n_before - len(G.nodes)} nodes)")

    print(f"\n=== Resolving destination nodes ===")
    # Each agent's home + destinations -> graph node ids, collect unique ones
    home_nodes: dict[str, int] = {}
    all_unique_nodes: set[int] = set()
    agent_trips: list[list[TripPlan]] = []

    t0 = time.time()
    for adata in all_agents_data:
        home_node = cached_nearest_node(G, adata.dorm_lon, adata.dorm_lat)
        home_nodes[adata.student_id] = home_node
        all_unique_nodes.add(home_node)

        trips = build_trips_for_day(adata, target_day, G)
        for tp in trips:
            all_unique_nodes.add(tp.dest_node)
        agent_trips.append(trips)
    print(f"  Resolved nodes for {len(all_agents_data)} agents in {time.time()-t0:.1f}s")
    print(f"  {len(all_unique_nodes)} unique destination nodes")

    print(f"\n=== Building path cache ===")
    path_cache, edge_lengths = build_path_cache(G, all_unique_nodes)

    print(f"\n=== Constructing agents ===")
    agents: list[Agent] = []

    for adata, trips in zip(all_agents_data, agent_trips):
        agents.append(Agent(
            student_id=adata.student_id,
            home_node=home_nodes[adata.student_id],
            speed=adata.speed,
            trips=trips,
            G=G, path_cache=path_cache, edge_lengths=edge_lengths,
        ))

    print(f"\n=== Running simulation: {SIM_START_SEC//3600:02d}:00 -> "
          f"{SIM_END_SEC//3600:02d}:00, dt={DT_SEC}s ===")
    out = SimOutput(timestamps=[], agent_ids=[], lats=[], lons=[], statuses=[], edge_us=[], edge_vs=[])
    sim_t0 = time.time()
    last_progress_t = SIM_START_SEC

    for t in range(SIM_START_SEC, SIM_END_SEC, DT_SEC):
        for agent in agents:
            agent.update(t, DT_SEC)

        if t % SAMPLE_EVERY == 0:
            for agent in agents:
                lat, lon = agent.position()
                u, v = agent.current_edge()
                out.timestamps.append(t)
                out.agent_ids.append(agent.student_id)
                out.lats.append(lat)
                out.lons.append(lon)
                out.statuses.append(agent.status)
                out.edge_us.append(u)
                out.edge_vs.append(v)

        # Progress prints every hr
        if t - last_progress_t >= 3600:
            statuses = Counter(a.status for a in agents)

            print(f"  t={t//3600:02d}:{(t%3600)//60:02d}  "
                f"home={statuses['home']:4d}  "
                f"between={statuses['between']:4d}  "
                f"moving={statuses['moving']:4d}  "
                f"in_class={statuses['in_class']:4d}  "
                f"done={statuses['done']:4d}")
            
            last_progress_t = t

    print(f"\nSim wall time: {time.time()-sim_t0:.1f}s")
    return out


def save_trajectory(out: SimOutput) -> Path:
    df = pd.DataFrame({
        "t": out.timestamps, "agent_id": out.agent_ids,
        "lat": out.lats, "lon": out.lons, "status": out.statuses,
        # nullable Int64 so non-moving rows stay NA, not NaN-as-float
        "u": pd.array(out.edge_us, dtype="Int64"),
        "v": pd.array(out.edge_vs, dtype="Int64"),
    })

    path = OUTPUTS / "trajectory.parquet"
    df.to_parquet(path, index=False)
    print(f"Wrote {len(df):,} trajectory rows to {path}")

    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="number of agents")
    ap.add_argument("--day", type=str, default="Monday", choices=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    args = ap.parse_args()

    out = run_simulation(args.n, args.day)
    save_trajectory(out)


if __name__ == "__main__":
    main()