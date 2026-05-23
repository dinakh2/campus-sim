# CONGESTION EVAL
#
# Edge-minute Level of Service from the proposal:
#   m^2/person = (edge_length * path_width) / unique_agents_on_edge_in_minute
#   <2.2 m^2/person  =>  LoS D or worse  =>  "congested"
# Outputs: per-minute peak time series, top-20 (edge, minute) pairs,
#          per-agent exposure fractions
#
# Three baselines (empty, single agent, fake crowd) exercise the metric
# without needing the campus graph or a real trajectory
#
#     python eval/congestion.py  # baselines + real if available
#     python eval/congestion.py --baselines-only

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import OUTPUTS

# HCM pedestrian LoS thresholds, m^2/person, descending
LOS_THRESHOLDS: list[tuple[str, float]] = [
    ("A", 3.7), ("B", 2.8), ("C", 2.2), ("D", 1.5), ("E", 0.7), ("F", 0.0),
]
CONGESTED_M2_PER_PERSON = 2.2  # < this LoS D or worse
DEFAULT_PATH_WIDTH_M = 2.0
DEFAULT_SAMPLE_DT_S = 30.0  # match sim/runner.py SAMPLE_EVERY


def los_grade(m2_per_person: float) -> str:
    if m2_per_person != m2_per_person:  # NaN
        return "A"
    for grade, threshold in LOS_THRESHOLDS:
        if m2_per_person >= threshold:
            return grade
    return "F"


# Trajectory rows in 'moving' state with a known (u, v) edge
def _moving_with_edges(traj: pd.DataFrame) -> pd.DataFrame:
    if "u" not in traj.columns or "v" not in traj.columns:
        return traj.iloc[0:0]
    mask = (traj["status"] == "moving") & traj["u"].notna() & traj["v"].notna()
    
    if not mask.any():
        return traj.iloc[0:0]
    
    out = traj.loc[mask].copy()
    out["u"] = out["u"].astype("int64")
    out["v"] = out["v"].astype("int64")
    return out


# For each (u, v, minute) bucket: unique agent count, edge area,
# m^2/person, LoS letter, congested flag, multiple samples of the same
# agent in the same minute count once
def compute_edge_minute_los(
    traj: pd.DataFrame,
    edge_lengths: dict[tuple[int, int], float],
    path_width: float = DEFAULT_PATH_WIDTH_M,
) -> pd.DataFrame:
    moving = _moving_with_edges(traj)
    cols = ["u", "v", "minute", "n_agents", "edge_length_m",
            "area_m2", "m2_per_person", "los", "congested"]
    if len(moving) == 0:
        return pd.DataFrame(columns=cols)

    moving["minute"] = (moving["t"] // 60).astype("int64")

    grouped = (moving.groupby(["u", "v", "minute"])["agent_id"]
                     .nunique()
                     .reset_index(name="n_agents"))

    grouped["edge_length_m"] = [
        edge_lengths.get((int(u), int(v)), 50.0)
        for u, v in zip(grouped["u"], grouped["v"])
    ]
    grouped["area_m2"] = grouped["edge_length_m"] * float(path_width)
    grouped["m2_per_person"] = grouped["area_m2"] / grouped["n_agents"].clip(lower=1)
    grouped["los"] = grouped["m2_per_person"].map(los_grade)
    grouped["congested"] = grouped["m2_per_person"] < CONGESTED_M2_PER_PERSON
    return grouped[cols]


# Per-minute total of agents on congested edges
# Sum across edges in a minte, if same agent is on two edgnes, double count
def peak_campus_congestion_timeseries(edge_min: pd.DataFrame) -> pd.Series:
    if len(edge_min) == 0:
        return pd.Series(dtype="int64", name="congested_agents")
    cong = edge_min[edge_min["congested"]]
    if len(cong) == 0:
        return pd.Series(dtype="int64", name="congested_agents",
                         index=pd.Index([], name="minute"))
    return cong.groupby("minute")["n_agents"].sum().rename("congested_agents")


# Top-k congested (edge, minute) pairs ranked by lowest m^2/person
def top_congested_pairs(edge_min: pd.DataFrame, k: int = 20) -> pd.DataFrame:
    cong = edge_min[edge_min["congested"]]
    if len(cong) == 0:
        return cong.iloc[0:0]
    return cong.nsmallest(k, "m2_per_person").reset_index(drop=True)


# Per agent: moving time, time on congested edges, exposure fraction
def agent_congestion_exposure(
    traj: pd.DataFrame,
    edge_min: pd.DataFrame,
    sample_dt_s: float = DEFAULT_SAMPLE_DT_S,

) -> pd.DataFrame:
    cols = ["agent_id", "moving_time_s", "congested_time_s", "exposure_frac"]
    moving = _moving_with_edges(traj)
    if len(moving) == 0:
        return pd.DataFrame(columns=cols)

    moving["minute"] = (moving["t"] // 60).astype("int64")

    cong_set = set(zip(
        edge_min.loc[edge_min["congested"], "u"].astype("int64"),
        edge_min.loc[edge_min["congested"], "v"].astype("int64"),
        edge_min.loc[edge_min["congested"], "minute"].astype("int64"),
    ))
    keys = list(zip(moving["u"], moving["v"], moving["minute"]))
    moving["on_congested"] = [k in cong_set for k in keys]

    by_agent = (moving.groupby("agent_id")
                       .agg(moving_samples=("t", "count"),
                            congested_samples=("on_congested", "sum"))
                       .reset_index())
    by_agent["moving_time_s"] = by_agent["moving_samples"] * float(sample_dt_s)
    by_agent["congested_time_s"] = by_agent["congested_samples"] * float(sample_dt_s)
    by_agent["exposure_frac"] = (by_agent["congested_time_s"]
                                  / by_agent["moving_time_s"].replace(0, np.nan)).fillna(0.0)
    return (by_agent[cols]
            .sort_values("exposure_frac", ascending=False)
            .reset_index(drop=True))


@dataclass
class EvalResult:
    n_moving_samples: int
    n_unique_agents_moving: int
    n_edges_observed: int
    n_congested_edge_minutes: int
    peak_congested_agents: int
    peak_minute: int | None  # minute-of-day when peak occurred
    peak_hhmm: str | None
    edge_minute: pd.DataFrame = field(repr=False)
    timeseries: pd.Series = field(repr=False)
    top_pairs: pd.DataFrame = field(repr=False)
    exposures: pd.DataFrame = field(repr=False)


def evaluate(
    traj: pd.DataFrame,
    edge_lengths: dict[tuple[int, int], float],
    path_width: float = DEFAULT_PATH_WIDTH_M,
    sample_dt_s: float = DEFAULT_SAMPLE_DT_S,
    top_k: int = 20,

) -> EvalResult:
    edge_min = compute_edge_minute_los(traj, edge_lengths, path_width)
    timeseries = peak_campus_congestion_timeseries(edge_min)
    top = top_congested_pairs(edge_min, k=top_k)
    exposures = agent_congestion_exposure(traj, edge_min, sample_dt_s)

    moving = _moving_with_edges(traj)
    if len(timeseries):
        peak_val = int(timeseries.max())
        peak_min = int(timeseries.idxmax())
        peak_hhmm = f"{peak_min // 60:02d}:{peak_min % 60:02d}"
    else:
        peak_val, peak_min, peak_hhmm = 0, None, None

    return EvalResult(
        n_moving_samples=int(len(moving)),
        n_unique_agents_moving=int(moving["agent_id"].nunique()) if len(moving) else 0,
        n_edges_observed=int(edge_min[["u", "v"]].drop_duplicates().shape[0]),
        n_congested_edge_minutes=int(edge_min["congested"].sum()) if len(edge_min) else 0,
        peak_congested_agents=peak_val,
        peak_minute=peak_min,
        peak_hhmm=peak_hhmm,
        edge_minute=edge_min,
        timeseries=timeseries,
        top_pairs=top,
        exposures=exposures,
    )


# ----- baselines ------------------------------------------------------------
# Synthesize tiny trajectories with the same schema as the real sim so the
# metric can be exercised end-to-end without the campus graph.

def _synth_traj(rows: list[dict]) -> pd.DataFrame:
    if rows:
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=["t", "agent_id", "status", "u", "v"])
    if "u" not in df.columns:
        df["u"] = pd.NA
    if "v" not in df.columns:
        df["v"] = pd.NA
    df["u"] = df["u"].astype("Int64")
    df["v"] = df["v"].astype("Int64")
    return df


# 0 rows -> peak=0, no congested edges
def baseline_empty() -> tuple[EvalResult, dict]:
    traj = _synth_traj([])
    edge_lengths = {(1, 2): 50.0}
    r = evaluate(traj, edge_lengths)

    checks = {
        "peak_is_zero": r.peak_congested_agents == 0,
        "no_congested_edge_minutes": r.n_congested_edge_minutes == 0,
        "no_top_pairs": len(r.top_pairs) == 0,
        "no_exposures": len(r.exposures) == 0,
    }
    return r, checks


# One agent on a 50m edge for 10 min: 150 m^2/person -> LoS A, never congested
def baseline_single_agent() -> tuple[EvalResult, dict]:
    rows = [
        {"t": t, "agent_id": "A0", "status": "moving", "u": 1, "v": 2}
        for t in range(0, 600, 30)
    ]
    traj = _synth_traj(rows)
    edge_lengths = {(1, 2): 50.0}
    r = evaluate(traj, edge_lengths)

    checks = {
        "peak_is_zero": r.peak_congested_agents == 0,
        "no_congested_edge_minutes": r.n_congested_edge_minutes == 0,
        "agent_observed_moving": r.n_unique_agents_moving == 1,
        "exposure_fraction_is_zero": (
            len(r.exposures) == 1 and float(r.exposures.iloc[0]["exposure_frac"]) == 0.0
        ),
    }
    return r, checks


# N agents on one 50m edge for one minute. 250/(50*3)=0.6 m^2/p -> LoS F
def baseline_fake_crowd(
    n_agents: int = 250,
    minute: int = 30,
    edge_length_m: float = 50.0,
    path_width: float = DEFAULT_PATH_WIDTH_M,
) -> tuple[EvalResult, dict]:
    rows = []
    t_base = minute * 60  # all samples in the same minute bucket
    for i in range(n_agents):
        rows.append({"t": t_base, "agent_id": f"A{i}", "status": "moving",
                     "u": 1, "v": 2})
    traj = _synth_traj(rows)
    edge_lengths = {(1, 2): edge_length_m}
    r = evaluate(traj, edge_lengths, path_width=path_width)

    expected_m2_per_person = (edge_length_m * path_width) / n_agents
    expected_los = los_grade(expected_m2_per_person)

    checks = {
        "peak_equals_n_agents": r.peak_congested_agents == n_agents,
        "peak_at_correct_minute": r.peak_minute == minute,
        "exactly_one_congested_edge_minute": r.n_congested_edge_minutes == 1,
        "top_edge_is_F": (
            len(r.top_pairs) >= 1 and r.top_pairs.iloc[0]["los"] == "F"
            and expected_los == "F"
        ),
        "all_agents_fully_exposed": (
            len(r.exposures) == n_agents
            and (r.exposures["exposure_frac"] == 1.0).all()
        ),
    }
    return r, checks


def _print_result_summary(name: str, r: EvalResult, checks: dict) -> None:
    print(f"\n{'=' * 64}")
    print(f"BASELINE: {name}")
    print("=" * 64)
    print(f"  moving samples     : {r.n_moving_samples}")
    print(f"  unique agents      : {r.n_unique_agents_moving}")
    print(f"  edges observed     : {r.n_edges_observed}")
    print(f"  congested edge-min : {r.n_congested_edge_minutes}")
    print(f"  peak congested     : {r.peak_congested_agents}"
          f"{'' if r.peak_hhmm is None else f' at {r.peak_hhmm}'}")
    if len(r.top_pairs):
        head = r.top_pairs.head(3)
        print(f"  top congested pairs:")
        for _, row in head.iterrows():
            print(f"    edge=({int(row['u'])},{int(row['v'])}) "
                  f"min={int(row['minute'])} n={int(row['n_agents'])} "
                  f"m2/p={row['m2_per_person']:.3f} los={row['los']}")
    print(f"  checks:")
    all_pass = True
    for k, v in checks.items():
        marker = "PASS" if v else "FAIL"
        if not v:
            all_pass = False
        print(f"    [{marker}] {k}")
    print(f"  -> {'PASS' if all_pass else 'FAIL'}")


def run_baselines() -> dict:
    summary: dict = {}

    r, checks = baseline_empty()
    _print_result_summary("empty trajectory", r, checks)
    summary["empty"] = {
        "peak_congested_agents": r.peak_congested_agents,
        "n_congested_edge_minutes": r.n_congested_edge_minutes,
        "checks": checks,
        "passed": all(checks.values()),
    }

    r, checks = baseline_single_agent()
    _print_result_summary("single agent", r, checks)
    summary["single_agent"] = {
        "moving_samples": r.n_moving_samples,
        "peak_congested_agents": r.peak_congested_agents,
        "n_congested_edge_minutes": r.n_congested_edge_minutes,
        "checks": checks,
        "passed": all(checks.values()),
    }

    r, checks = baseline_fake_crowd()
    top_los = r.top_pairs.iloc[0]["los"] if len(r.top_pairs) else None
    top_m2 = float(r.top_pairs.iloc[0]["m2_per_person"]) if len(r.top_pairs) else None
    _print_result_summary("fake crowd (250 agents on 50 m edge, 1 min)", r, checks)
    summary["fake_crowd"] = {
        "n_agents": 250,
        "peak_congested_agents": r.peak_congested_agents,
        "peak_minute": r.peak_minute,
        "peak_hhmm": r.peak_hhmm,
        "top_los": top_los,
        "top_m2_per_person": top_m2,
        "checks": checks,
        "passed": all(checks.values()),
    }

    summary["all_passed"] = all(s["passed"] for s in summary.values() if isinstance(s, dict) and "passed" in s)
    return summary


# ----- real trajectory eval -------------------------------------------------

def _load_graph_edge_lengths() -> dict[tuple[int, int], float]:
    import osmnx as ox
    print("Loading campus graph for edge lengths...")
    G = ox.graph_from_place("Stanford University, California", network_type="walk")
    G = ox.truncate.largest_component(G, strongly=False)

    edge_lengths: dict[tuple[int, int], float] = {}

    for u, v, data in G.edges(data=True):
        length = data.get("length", 50.0)
        if (u, v) not in edge_lengths or length < edge_lengths[(u, v)]:
            edge_lengths[(u, v)] = length

    print(f"  {len(G.nodes)} nodes, {len(edge_lengths)} unique directed edges")
    return edge_lengths


# Return None if trajectory has no (u, v) columns
def evaluate_real_trajectory(traj_path: Path) -> EvalResult | None:
    print(f"\nLoading trajectory: {traj_path}")
    traj = pd.read_parquet(traj_path)
    print(f"  {len(traj):,} rows; columns: {list(traj.columns)}")

    if "u" not in traj.columns or "v" not in traj.columns:
        print("  Trajectory has no (u, v) edge columns. Re-run sim/runner.py "
              "after this update so per-edge congestion can be computed.")
        return None

    edge_lengths = _load_graph_edge_lengths()
    print("Computing edge-minute LoS...")
    return evaluate(traj, edge_lengths)


def _result_to_summary(r: EvalResult) -> dict:
    top = r.top_pairs.head(20).copy()

    if len(top):
        top["u"] = top["u"].astype(int)
        top["v"] = top["v"].astype(int)

    exp = r.exposures.head(20)
    return {
        "n_moving_samples": r.n_moving_samples,
        "n_unique_agents_moving": r.n_unique_agents_moving,
        "n_edges_observed": r.n_edges_observed,
        "n_congested_edge_minutes": r.n_congested_edge_minutes,
        "peak_congested_agents": r.peak_congested_agents,
        "peak_minute": r.peak_minute,
        "peak_hhmm": r.peak_hhmm,
        "top_20_congested_pairs": top.to_dict(orient="records"),
        "top_20_exposed_agents": exp.to_dict(orient="records"),
    }


# ----- CLI ------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trajectory", type=Path, default=None,
                    help="path to trajectory.parquet (default: outputs/trajectory.parquet)")
    ap.add_argument("--baselines-only", action="store_true",
                    help="skip real-trajectory eval")
    args = ap.parse_args()

    OUTPUTS.mkdir(parents=True, exist_ok=True)

    summary: dict = {"baselines": run_baselines()}

    if not args.baselines_only:
        traj_path = args.trajectory or (OUTPUTS / "trajectory.parquet")
        if not traj_path.exists():
            summary["real"] = {"skipped": True, "reason": f"{traj_path} not found"}
            print(f"\nReal eval skipped: {traj_path} not found")
        else:
            r = evaluate_real_trajectory(traj_path)
            if r is None:
                summary["real"] = {
                    "skipped": True,
                    "reason": "trajectory lacks (u, v) edge columns; "
                              "re-run sim/runner.py to regenerate",
                }
            else:
                summary["real"] = _result_to_summary(r)
                # Persist the full edge-minute table for downstream viz/analysis
                edge_min_path = OUTPUTS / "edge_minute_los.parquet"
                r.edge_minute.to_parquet(edge_min_path, index=False)

                print(f"\nWrote {edge_min_path} ({len(r.edge_minute):,} rows)")
                print(f"Peak: {r.peak_congested_agents} agents on congested "
                      f"edges at {r.peak_hhmm}")

    out_path = OUTPUTS / "congestion_baseline.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
