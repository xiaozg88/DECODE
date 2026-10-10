import os
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx

from common import OUT, seg_path


# 13 countries with the smallest noded networks (<= ~950k segments) so graph
# construction stays tractable; larger countries are left for a future tiled run.
SMALL = ["PNG", "KGZ", "RWA", "JOR", "HND", "KHM", "GEO", "ZMB",
         "GTM", "GHA", "LKA", "SEN", "MLI"]


def graph_stats(iso, seg):
    edges = []
    lens = seg["length_m"].to_numpy(dtype="float64")
    geoms = seg.geometry
    for i, geom in enumerate(geoms):
        if geom is None or geom.is_empty or geom.geom_type != "LineString":
            continue
        coords = list(geom.coords)
        if len(coords) < 2:
            continue
        a = (round(coords[0][0], 6), round(coords[0][1], 6))
        b = (round(coords[-1][0], 6), round(coords[-1][1], 6))
        if a == b:
            continue
        edges.append((a, b, float(lens[i])))
    G = nx.Graph()
    G.add_weighted_edges_from(edges, weight="length")
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    comps = list(nx.connected_components(G))
    largest = max(len(c) for c in comps) if comps else 0
    bridges = list(nx.bridges(G))
    deg1 = sum(1 for _n, d in G.degree() if d == 1)
    bridge_len = sum(G[a][b].get("length", 0.0) for a, b in bridges)
    total_len = float(lens.sum())
    return {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "n_components": len(comps),
        "connectivity_share": largest / n_nodes if n_nodes else np.nan,
        "n_bridges": len(bridges),
        "bridge_length_share": bridge_len / total_len if total_len else np.nan,
        "avg_degree": (2.0 * n_edges / n_nodes) if n_nodes else np.nan,
        "deg1_node_share": deg1 / n_nodes if n_nodes else np.nan,
    }


def run():
    rows = []
    for iso in SMALL:
        rec = {"iso3": iso}
        try:
            seg = gpd.read_file(seg_path(iso))
            rec["n_segments"] = len(seg)
            rec["total_length_km"] = float(seg["length_m"].sum()) / 1000.0
            rec.update(graph_stats(iso, seg))
        except Exception as exc:
            rec["error"] = repr(exc)[:200]
        rows.append(rec)
        print(iso, "done", flush=True)
    df = pd.DataFrame(rows)
    out = os.path.join(OUT, "d04_redundancy.csv")
    df.to_csv(out, index=False)
    print(df.round(4).to_string())
    print("saved", out)


if __name__ == "__main__":
    run()

