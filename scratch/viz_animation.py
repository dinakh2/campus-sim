import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
import pandas as pd

from paths import OUTPUTS

START_HOUR  = 5  # animation start
END_HOUR = 21  # animation end
FRAME_EVERY = 60  # one frame per N simulation seconds
FPS = 15  # playback speed: 15 fps × 60s/frame = 15 min of sim per real second
JITTER = 0.0002  # ~20m, so stacked agents fan out a little

STYLES = {
    # ---- moving ----
    ("moving", "class"):     {"color": "#e63946", "s": 14, "alpha": 0.80, "zorder": 8, "label": "→ class"},
    ("moving", "coffee"):    {"color": "#8b5a2b", "s": 12, "alpha": 0.85, "zorder": 8, "label": "→ coffee"},
    ("moving", "lunch"):     {"color": "#ff9f1c", "s": 12, "alpha": 0.85, "zorder": 8, "label": "→ lunch"},
    ("moving", "library"):   {"color": "#1f6feb", "s": 12, "alpha": 0.80, "zorder": 8, "label": "→ library"},
    ("moving", "home_stop"): {"color": "#2a9d8f", "s": 12, "alpha": 0.80, "zorder": 8, "label": "→ home (break)"},
    ("moving", "dinner"):    {"color": "#d62828", "s": 12, "alpha": 0.85, "zorder": 8, "label": "→ dinner"},
    ("moving", "gym"):       {"color": "#ff006e", "s": 13, "alpha": 0.85, "zorder": 8, "label": "→ gym"},
    ("moving", "go_home"):   {"color": "#7e57c2", "s": 12, "alpha": 0.75, "zorder": 8, "label": "→ home (end)"},
    ("moving", "_other_"):   {"color": "#444444", "s": 10, "alpha": 0.60, "zorder": 7, "label": "→ moving"},  # fallback
    
    # ---- static at dest ----
    ("in_class", "class"):     {"color": "#457b9d", "s": 4, "alpha": 0.30, "zorder": 3, "label": "in class"},
    ("in_class", "coffee"):    {"color": "#c69a6e", "s": 5, "alpha": 0.45, "zorder": 4, "label": "at coffee"},
    ("in_class", "lunch"):     {"color": "#ffd166", "s": 5, "alpha": 0.50, "zorder": 4, "label": "at lunch"},
    ("in_class", "library"):   {"color": "#74a8d4", "s": 4, "alpha": 0.45, "zorder": 4, "label": "at library"},
    ("in_class", "home_stop"): {"color": "#88c5b6", "s": 4, "alpha": 0.35, "zorder": 3, "label": "at home (break)"},
    ("in_class", "dinner"):    {"color": "#e07a5f", "s": 5, "alpha": 0.50, "zorder": 4, "label": "at dinner"},
    ("in_class", "gym"):       {"color": "#ff5c8a", "s": 5, "alpha": 0.55, "zorder": 4, "label": "at gym"},
    ("in_class", "_other_"):   {"color": "#457b9d", "s": 4, "alpha": 0.30, "zorder": 3, "label": "in class"},
    
    # ---- other states ----
    ("home", None):    {"color": "#7ec97e", "s": 3, "alpha": 0.45, "zorder": 2, "label": "home"},
    ("between", None): {"color": "#d4a373", "s": 3, "alpha": 0.40, "zorder": 3, "label": "between"},
    ("done", None):    {"color": "#5a3a8a", "s": 3, "alpha": 0.50, "zorder": 2, "label": "done"},
}

SPLIT_BY_PURPOSE = {"moving", "in_class"}
PURPOSE_BUCKETS = ["class", "coffee", "lunch", "library", "home_stop", "dinner", "gym", "go_home"]


print("Loading trajectory...")
df = pd.read_parquet(OUTPUTS / "trajectory.parquet")

has_purpose = "purpose" in df.columns
if not has_purpose:
    print("  (trajectory has no `purpose` column — coloring all moving agents the same)")
    df["purpose"] = ""

# Pre-filter to the time range and to sample points that are multiples of FRAME_EVERY
df = df[(df["t"] >= START_HOUR * 3600) & (df["t"] < END_HOUR * 3600)]
df = df[df["t"] % FRAME_EVERY == 0]
print(f"  {len(df):,} samples will animate")

# Group by timestamp once
frames = sorted(df["t"].unique())
print(f"  {len(frames)} frames covering {(frames[-1]-frames[0])/3600:.1f}h")

groups = {t: g for t, g in df.groupby("t")}

print("Loading campus graph...")
G = ox.graph_from_place("Stanford University, California", network_type="walk")

print("Setting up figure...")
fig, ax = ox.plot_graph(
    G, show=False, close=False,
    node_size=0, edge_linewidth=0.5,
    edge_color="#444444",
    bgcolor="#f5f5f5",
    figsize=(12, 12)
)

scatters: dict[tuple[str, str | None], plt.Artist] = {}
for key, style in STYLES.items():
    label = style.get("label")
    kwargs = {k: v for k, v in style.items() if k != "label"}
    scatters[key] = ax.scatter([], [], **kwargs, label=label)

clock = ax.text(0.02, 0.98, "", transform=ax.transAxes, fontsize=18,
                verticalalignment="top", fontweight="bold",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

ax.legend(loc="upper right", fontsize=9, ncol=2)
ax.set_title("Stanford campus — Monday simulation (Tier 1+2 behaviors)", fontsize=14)

done_seen: set = set()

# Deterministic jitter to make overlapping points seen
rng = np.random.default_rng(0)
jitter_lookup: dict = {}

def get_jitter(agent_ids):
    dx = np.empty(len(agent_ids))
    dy = np.empty(len(agent_ids))
    for i, aid in enumerate(agent_ids):
        if aid not in jitter_lookup:
            jitter_lookup[aid] = (rng.normal(0, JITTER), rng.normal(0, JITTER))
        dx[i], dy[i] = jitter_lookup[aid]
    return dx, dy


def bucket_key(status: str, purpose: str) -> tuple[str, str | None]:
    if status not in SPLIT_BY_PURPOSE:
        return (status, None)
    if purpose in PURPOSE_BUCKETS:
        return (status, purpose)
    return (status, "_other_")


def animate(i):
    t = frames[i]
    g = groups.get(t)
    if g is None:
        return list(scatters.values()) + [clock]

    # Bucket rows by (status, purpose) once for this frame
    g_keys = [bucket_key(s, p) for s, p in zip(g["status"].values, g["purpose"].values)]
    g = g.assign(_bucket=g_keys)

    for key, sc in scatters.items():
        sub = g[g["_bucket"] == key]
        if len(sub) == 0:
            sc.set_offsets(np.empty((0, 2)))
        else:
            dx, dy = get_jitter(sub["agent_id"].values)
            xs = sub["lon"].values + dx
            ys = sub["lat"].values + dy
            sc.set_offsets(np.column_stack([xs, ys]))

    h, m = t // 3600, (t % 3600) // 60
    counts = g["status"].value_counts()
    purpose_moving = g[g["status"] == "moving"]["purpose"].value_counts()

    done_now = g.loc[g["status"] == "done", "agent_id"]
    if len(done_now):
        done_seen.update(done_now.values)

    moving_breakdown = "  ".join(
        f"{p}:{int(purpose_moving.get(p, 0))}" for p in PURPOSE_BUCKETS
        if purpose_moving.get(p, 0) > 0
    )
    clock.set_text(
        f"{h:02d}:{m:02d}\n"
        f"moving: {counts.get('moving', 0)}\n"
        f"  {moving_breakdown}\n"
        f"in class/dest: {counts.get('in_class', 0)}\n"
        f"done: {len(done_seen)}"
    )

    return list(scatters.values()) + [clock]


print(f"Rendering {len(frames)} frames at {FPS}fps...")
anim = animation.FuncAnimation(
    fig, animate, frames=len(frames), interval=1000/FPS, blit=False
)

out = OUTPUTS / "animation.mp4"
try:
    anim.save(out, writer="ffmpeg", fps=FPS, dpi=120, bitrate=2400)
    print(f"Saved {out}")
except Exception as e:
    print(f"MP4 failed ({e}), falling back to GIF")
    out = OUTPUTS / "animation.gif"
    anim.save(out, writer="pillow", fps=FPS, dpi=80)
    print(f"Saved {out}")
