import sys
from pathlib import Path

import osmnx as ox
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import OUTPUTS
from map_buildings import DORM_LOCATIONS, BUILDING_LOCATIONS

rng = np.random.default_rng(42)

print("Loading campus graph...")
G = ox.graph_from_place("Stanford University, California", network_type="walk")
print(f"Graph: {len(G.nodes)} nodes, {len(G.edges)} edges")

# Helper: pick first edge key and return length
def edge_length(u, v):
    edge_data = G[u][v]
    key = min(edge_data.keys())
    return edge_data[key].get("length", 50)  # fallback if length missing

# Helper: get lat long position for agent
def agent_position(agent):
    if agent.status == "moving" and len(agent.path) >= 2:
        u, v = agent.path[0], agent.path[1]
        length = edge_length(u, v)
        frac = agent.path_progress / length if length > 0 else 0

        lat_u, lon_u = G.nodes[u]['y'], G.nodes[u]['x']
        lat_v, lon_v = G.nodes[v]['y'], G.nodes[v]['x']

        return (lat_u + frac * (lat_v - lat_u), lon_u + frac * (lon_v - lon_u))
    
    n = agent.current_node
    return (G.nodes[n]['y'], G.nodes[n]['x'])

def hhmm(sec):
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}"

# Random dorm home and class destination for testing
home_name, home_lat, home_lon = DORM_LOCATIONS["Alondra"]
dest_name, dest_lat, dest_lon = BUILDING_LOCATIONS["Gates"]

home_node = ox.nearest_nodes(G, home_lon, home_lat)
dest_node = ox.nearest_nodes(G, dest_lon, dest_lat)
print(f"Home: {home_name} -> node {home_node}")
print(f"Dest: {dest_name} -> node {dest_node}")

class Agent:
    def __init__(self, home_node, schedule, speed=1.4):  # change speed later
        self.current_node = home_node
        self.path = []
        self.path_progress = 0.0
        self.speed = speed
        self.status = "home"
        self.schedule = sorted(schedule, key=lambda c: c["start_sec"])
        self.buffer = max(30, rng.normal(3*60, 60))  # randomize how much buffer people leave from est travel time

    def next_class(self, t):
        for c in self.schedule:
            if c["start_sec"] > t:
                return c
        return None
    
    def estimate_travel_time(self, dest):
        try:
            length = nx.shortest_path_length(G, self.current_node, dest, weight="length")
            return length / self.speed
        
        except nx.NetworkXNoPath:
            return float("inf")

    def update(self, t, dt):
        # Decide whether to leave
        if self.status == "home":
            nxt = self.next_class(t)

            if nxt is not None:
                travel = self.estimate_travel_time(nxt["location"])
                depart = nxt["start_sec"] - self.buffer - travel

                if t >= depart:
                    try:
                        self.path = nx.shortest_path(G, self.current_node, nxt["location"], weight="length")
                        self.status = "moving"
                        self.path_progress = 0.0
                    except nx.NetworkXNoPath:
                        pass  # stay home if no path

        # Move along path
        if self.status == "moving" and len(self.path) >= 2:
            u, v = self.path[0], self.path[1]
            length = edge_length(u, v)
            self.path_progress += self.speed * dt

            if self.path_progress >= length:
                self.path_progress = 0.0
                self.path.pop(0)
                self.current_node = self.path[0]  # bug fix
                if len(self.path) < 2:
                    self.status = "in_class"
                    self.path = []

# Schedule
schedule = [{"location": dest_node, "start_sec": 9*3600, "end_sec": 10*3600}]
agent = Agent(home_node, schedule)

# Run from 8:30 to 9:15
trajectory = []
for t in range(8*3600 + 30*60, 9*3600 + 15*60, 10):
    agent.update(t, dt=10)
    lat, lon = agent_position(agent)
    trajectory.append((t, lat, lon, agent.status))

print(f"Recorded {len(trajectory)} frames")

import matplotlib.pyplot as plt
import matplotlib.animation as animation

print("Building base map...")
fig, ax = ox.plot_graph(
    G, show=False, close=False,
    node_size=0, edge_linewidth=0.5,
    edge_color="#cccccc", bgcolor="white", figsize=(10, 10)
)

# Empty dot and text we'll update each frame
dot, = ax.plot([], [], 'o', color='red', markersize=12, zorder=5)
clock = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                fontsize=14, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

def init():
    dot.set_data([], [])
    clock.set_text('')
    return dot, clock

def animate(i):
    t, lat, lon, status = trajectory[i]
    dot.set_data([lon], [lat])  # matplotlib: x=lon, y=lat
    clock.set_text(f"{hhmm(t)} — {status}")
    return dot, clock

print("Rendering animation...")
anim = animation.FuncAnimation(
    fig, animate, init_func=init,
    frames=len(trajectory), interval=50, blit=True
)

anim.save(OUTPUTS / "agent.gif", writer='pillow', fps=30)
print(f"Saved {OUTPUTS / 'agent.gif'}")