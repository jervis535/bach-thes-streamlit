"""Single source of truth for cluster colors.

Cluster 0 is always red, cluster 1 always blue, and so on, in every
plot (scatter, silhouette, profile trends, map).
"""

import matplotlib.pyplot as plt

# Fixed colors per cluster id. Light grey is left out on purpose,
# because the map uses it for "no data".
CLUSTER_PALETTE = [
    "#E41A1C",  # 0 red
    "#1F77B4",  # 1 blue
    "#2CA02C",  # 2 green
    "#FF7F0E",  # 3 orange
    "#9467BD",  # 4 purple
    "#8C564B",  # 5 brown
    "#E377C2",  # 6 pink
    "#17BECF",  # 7 cyan
    "#BCBD22",  # 8 olive
    "#000000",  # 9 black
]


def get_cluster_color(cluster_id):
    """Return the color for one cluster id (int or float like 2.0)."""
    i = int(cluster_id)

    if i < len(CLUSTER_PALETTE):
        return CLUSTER_PALETTE[i]

    # More clusters than palette entries: continue with tab20
    return plt.get_cmap("tab20")(i % 20)


def get_cluster_colors(cluster_ids):
    """Return {cluster_id: color} for an iterable of cluster ids."""
    return {cid: get_cluster_color(cid) for cid in cluster_ids}