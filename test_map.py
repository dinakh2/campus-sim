import osmnx as ox
import matplotlib.pyplot as plt

G = ox.graph_from_place("Stanford University, California", network_type="walk")

print(f"Nodes: {len(G.nodes)}")
print(f"Edges: {len(G.edges)}")

fig, ax = ox.plot_graph(
    G,
    figsize=(12, 12),
    node_size=5,
    node_color="#333333",
    edge_linewidth=0.8,
    edge_color="#333333",
    bgcolor="white",
    show=False,
    close=False,
    save=True,
    filepath="stanford_map.png",
    dpi=150
)

print("Saved stanford_map.png")

# Check if key buildings snap to nearby nodes
test_buildings = {
    "Gates": (37.4302, -122.1753),
    "Main Quad": (37.4274, -122.1700),
    "White Plaza": (37.4268, -122.1695),
}

for name, (lat, lon) in test_buildings.items():
    node = ox.nearest_nodes(G, lon, lat)
    print(f"{name}: nearest node {node}")