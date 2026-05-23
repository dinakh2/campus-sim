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
from sim.load_data import load_agents
from sim.agent import Agent, TripPlan
from sim.trip_planner import build_trips_for_day
from pipeline import behavior_params as bp


# Sim params
SIM_START_SEC = 6 * 3600  # 06:00
SIM_END_SEC = 22 * 3600  # 22:00
# DT_SEC must be <= SAMPLE_EVERY
DT_SEC = bp.SAMPLE_EVERY_SEC
SAMPLE_EVERY = bp.SAMPLE_EVERY_SEC


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
    # purpose of agent's current trip (class/coffee/lunch/home_stop/go_home/"")
    purposes: list[str]

# Node Caching 
_nearest_node_cache = {}

def cached_nearest_node(G, lon, lat):
    key = (round(lat, 6), round(lon, 6))  # 6 decimal = ~10cm precision

    if key not in _nearest_node_cache:
        _nearest_node_cache[key] = ox.nearest_nodes(G, lon, lat)

    return _nearest_node_cache[key]

# Build a composed (walk + bike) graph with per-edge mode-access flags and mode-specific routing weights:
#   walk_weight = length if edge is walk-accessible, else +inf
#   bike_weight = length if edge is bike-accessible,
#                 length * WALK_ON_BIKE_PENALTY if walk-only (biker dismounts),
#                 +inf otherwise
# Returns (G, walk_edge_set, bike_edge_set). The (u, v) sets are useful for the
# agent's per-edge dismount-speed check.
def load_composed_graph() -> tuple:
    print("Loading walk graph...")
    G_walk = ox.graph_from_place("Stanford University, California", network_type="walk")
    print(f"  {len(G_walk.nodes)} nodes, {len(G_walk.edges)} edges")

    print("Loading bike graph...")
    G_bike = ox.graph_from_place("Stanford University, California", network_type="bike")
    print(f"  {len(G_bike.nodes)} nodes, {len(G_bike.edges)} edges")

    print("Composing + tagging edges...")
    G = nx.compose(G_walk, G_bike)
    # Keep largest connected (weakly) component so every (home, dest) pair has a path through at least one mode
    n_before = len(G.nodes)
    G = ox.truncate.largest_component(G, strongly=False)

    # Dead end nodes
    n_dead = 0
    while True:
        dead = [n for n in G.nodes if G.out_degree(n) == 0 or G.in_degree(n) == 0]
        if not dead:
            break
        G.remove_nodes_from(dead)
        n_dead += len(dead)

    print(f"  Composed: {len(G.nodes)} nodes, {len(G.edges)} edges "
          f"(dropped {n_before - len(G.nodes)} disconnected, {n_dead} dead-end)")

    walk_edges = {(u, v) for u, v in G_walk.edges()}
    bike_edges = {(u, v) for u, v in G_bike.edges()}

    INF = float("inf")
    n_walk_ok = n_bike_ok = 0
    for u, v, data in G.edges(data=True):
        in_walk = (u, v) in walk_edges or (v, u) in walk_edges
        in_bike = (u, v) in bike_edges or (v, u) in bike_edges
        length = float(data.get("length", 50.0))
        data["walk_ok"] = in_walk
        data["bike_ok"] = in_bike
        data["walk_weight"] = length if in_walk else INF
        if in_bike:
            data["bike_weight"] = length
        elif in_walk:
            data["bike_weight"] = length * bp.WALK_ON_BIKE_PENALTY
        else:
            data["bike_weight"] = INF
        n_walk_ok += in_walk
        n_bike_ok += in_bike

    print(f"  Edge access: walk_ok={n_walk_ok}, bike_ok={n_bike_ok}")
    return G, walk_edges, bike_edges


# Build separate path caches keyed by mode-specific edge weights
# Returns:
#   path_cache_walk: shortest paths using walk_weight (walk-accessible edges)
#   path_cache_bike: shortest paths using bike_weight (all edges, walk-only penalized)
#   edge_lengths: raw lengths for sim-time progress integration
#   edge_walk_ok: (u,v) -> bool, for biker dismount detection
#   edge_bike_ok: (u,v) -> bool, for biker dismount detection

def build_path_caches(G, all_nodes: set[int]) -> tuple[dict, dict, dict, dict, dict]:
    print(f"Precomputing per-mode shortest paths among {len(all_nodes)} unique nodes...")
    nodes_list = list(all_nodes)

    path_cache_walk: dict[tuple[int, int], list[int]] = {}
    path_cache_bike: dict[tuple[int, int], list[int]] = {}

    for mode_name, weight_attr, cache in (("walk", "walk_weight", path_cache_walk),
                                            ("bike", "bike_weight", path_cache_bike)):
        t0 = time.time()
        missing = 0
        for i, src in enumerate(nodes_list):
            if i % 20 == 0:
                print(f"  [{mode_name}] {i}/{len(nodes_list)}...")
            _, paths = nx.single_source_dijkstra(G, src, weight=weight_attr)
            for dst in nodes_list:
                if dst in paths:
                    cache[(src, dst)] = paths[dst]
                elif src != dst:
                    missing += 1
        print(f"  [{mode_name}] {len(cache)} paths in {time.time()-t0:.1f}s"
              f"{f' (missing {missing})' if missing else ''}")

    # edge_lengths: take the min raw length per (u, v)
    # for sim progress
    edge_lengths: dict[tuple[int, int], float] = {}
    edge_walk_ok: dict[tuple[int, int], bool] = {}
    edge_bike_ok: dict[tuple[int, int], bool] = {}
    for u, v, data in G.edges(data=True):
        length = float(data.get("length", 50.0))
        if (u, v) not in edge_lengths or length < edge_lengths[(u, v)]:
            edge_lengths[(u, v)] = length
            edge_walk_ok[(u, v)] = bool(data.get("walk_ok", True))
            edge_bike_ok[(u, v)] = bool(data.get("bike_ok", True))

    return path_cache_walk, path_cache_bike, edge_lengths, edge_walk_ok, edge_bike_ok

# Main sim
def run_simulation(n_agents: int = 100, target_day: str = "Monday") -> SimOutput:
    print(f"=== Loading data ===")
    all_agents_data = load_agents()

    if n_agents < len(all_agents_data):
        rng = np.random.default_rng(42)
        idx = rng.choice(len(all_agents_data), n_agents, replace=False)
        all_agents_data = [all_agents_data[i] for i in idx]

    print(f"Simulating {len(all_agents_data)} agents on {target_day}")

    print(f"\n=== Loading campus graph (multimodal: walk + bike) ===")
    t0 = time.time()
    G, _walk_edges, _bike_edges = load_composed_graph()
    print(f"  Graph load + tag: {time.time()-t0:.1f}s")

    print(f"\n=== Resolving destination nodes ===")
    # Each agent's home + destinations -> graph node ids, collect unique ones
    home_nodes: dict[str, int] = {}
    all_unique_nodes: set[int] = set()
    agent_trips: list[list[TripPlan]] = []

    t0 = time.time()
    # how many agents have at least one trip whose dest_node collides with their home_node? 
    agents_with_home_collision = 0
    total_home_collisions = 0
    total_trips = 0
    for adata in all_agents_data:
        home_node = cached_nearest_node(G, adata.dorm_lon, adata.dorm_lat)
        home_nodes[adata.student_id] = home_node
        all_unique_nodes.add(home_node)

        trips = build_trips_for_day(adata, target_day, G, cached_nearest_node)
        
        class_trips = [tp for tp in trips if tp.purpose not in ("go_home", "home_stop")]
        collisions = sum(1 for tp in class_trips if tp.dest_node == home_node)
        if collisions:
            agents_with_home_collision += 1
            total_home_collisions += collisions
        total_trips += len(class_trips)
        for tp in trips:
            all_unique_nodes.add(tp.dest_node)
        agent_trips.append(trips)

    print(f"  Resolved nodes for {len(all_agents_data)} agents in {time.time()-t0:.1f}s")
    print(f"  {len(all_unique_nodes)} unique destination nodes")
    
    if total_home_collisions:
        pct_agents = 100.0 * agents_with_home_collision / max(len(all_agents_data), 1)
        pct_trips = 100.0 * total_home_collisions / max(total_trips, 1)
        print(f"  home==dest collisions: {total_home_collisions}/{total_trips} trips "
              f"({pct_trips:.1f}%) across {agents_with_home_collision} agents ({pct_agents:.1f}%)")

    print(f"\n=== Building path caches (walk + bike) ===")
    (path_cache_walk, path_cache_bike,
     edge_lengths, edge_walk_ok, edge_bike_ok) = build_path_caches(G, all_unique_nodes)

    print(f"\n=== Constructing agents ===")
    agents: list[Agent] = []

    for adata, trips in zip(all_agents_data, agent_trips):
        agents.append(Agent(
            student_id=adata.student_id,
            home_node=home_nodes[adata.student_id],
            speed=adata.speed,
            mode=adata.mode,
            trips=trips,
            G=G,
            path_cache_walk=path_cache_walk,
            path_cache_bike=path_cache_bike,
            edge_lengths=edge_lengths,
            edge_walk_ok=edge_walk_ok,
            edge_bike_ok=edge_bike_ok,
        ))

    print(f"\n=== Running simulation: {SIM_START_SEC//3600:02d}:00 -> "
          f"{SIM_END_SEC//3600:02d}:00, dt={DT_SEC}s ===")
    out = SimOutput(timestamps=[], agent_ids=[], lats=[], lons=[], statuses=[],
                    edge_us=[], edge_vs=[], purposes=[])
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
                out.purposes.append(agent.current_purpose())

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

    total_skipped = sum(a.n_skipped_walks for a in agents)
    if total_skipped:
        n_affected = sum(1 for a in agents if a.n_skipped_walks > 0)
        print(f"Skipped walks (home==dest node, no path to walk): "
              f"{total_skipped} trips across {n_affected} agents")

    return out


def save_trajectory(out: SimOutput) -> Path:
    df = pd.DataFrame({
        "t": out.timestamps, "agent_id": out.agent_ids,
        "lat": out.lats, "lon": out.lons, "status": out.statuses,
        # nullable Int64 so non-moving rows stay NA, not NaN-as-float
        "u": pd.array(out.edge_us, dtype="Int64"),
        "v": pd.array(out.edge_vs, dtype="Int64"),
        "purpose": out.purposes,
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