"""Animate agents moving across campus over the simulated day."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
import pandas as pd

from paths import OUTPUTS

# ---------------- tunables ----------------
START_HOUR  = 7  # animation start
END_HOUR = 20  # animation end
FRAME_EVERY = 60  # one frame per N simulation seconds
FPS = 15  # playback speed: 15 fps × 60s/frame = 15 min of sim per real second
JITTER = 0.0002  # ~20m, so stacked agents fan out a little

print("Loading trajectory...")
df = pd.read_parquet(OUTPUTS / "trajectory.parquet")

# Pre-filter to the time range and to sample points that are multiples of FRAME_EVERY
df = df[(df["t"] >= START_HOUR * 3600) & (df["t"] < END_HOUR * 3600)]
df = df[df["t"] % FRAME_EVERY == 0]
print(f"  {len(df):,} samples will animate")

# Group by timestamp once — much faster than filtering at each frame
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

# Set up scatter artists per status (we update their data each frame)
status_styles = {
    "moving":   {"color": "red",       "s": 12, "alpha": 0.7, "zorder": 6},
    "between":  {"color": "orange",    "s": 4,  "alpha": 0.4, "zorder": 4},
    "in_class": {"color": "steelblue", "s": 4,  "alpha": 0.3, "zorder": 3},
    "home":     {"color": "#7ec97e",   "s": 3,  "alpha": 0.45, "zorder": 2},
    "done":     {"color": "#5a3a8a",   "s": 3,  "alpha": 0.5, "zorder": 2},
}
scatters = {}
for status, style in status_styles.items():
    scatters[status] = ax.scatter([], [], **style, label=status)

clock = ax.text(0.02, 0.98, "", transform=ax.transAxes, fontsize=18,
                verticalalignment="top", fontweight="bold",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

ax.legend(loc="upper right", fontsize=10)
ax.set_title("Stanford campus — Monday simulation", fontsize=14)

# done is monotonic; track cumulative set so the count doesn't flicker to 0
# on frames where no done agents happened to land in the sample
done_seen: set = set()

# Deterministic per-agent jitter (consistent across frames)
rng = np.random.default_rng(0)
jitter_lookup = {}

def get_jitter(agent_ids):
    dx = np.empty(len(agent_ids))
    dy = np.empty(len(agent_ids))
    for i, aid in enumerate(agent_ids):
        if aid not in jitter_lookup:
            jitter_lookup[aid] = (rng.normal(0, JITTER), rng.normal(0, JITTER))
        dx[i], dy[i] = jitter_lookup[aid]
    return dx, dy


def animate(i):
    t = frames[i]
    g = groups.get(t)
    if g is None:
        return list(scatters.values()) + [clock]

    for status, sc in scatters.items():
        sub = g[g["status"] == status]
        if len(sub) == 0:
            sc.set_offsets(np.empty((0, 2)))
        else:
            dx, dy = get_jitter(sub["agent_id"].values)
            xs = sub["lon"].values + dx
            ys = sub["lat"].values + dy
            sc.set_offsets(np.column_stack([xs, ys]))

    h, m = t // 3600, (t % 3600) // 60
    counts = g["status"].value_counts()

    done_now = g.loc[g["status"] == "done", "agent_id"]
    if len(done_now):
        done_seen.update(done_now.values)

    clock.set_text(
        f"{h:02d}:{m:02d}\n"
        f"moving: {counts.get('moving', 0)}\n"
        f"in class: {counts.get('in_class', 0)}\n"
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