import re
import difflib

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from pathlib import Path


# Path to the GADM level-2 shapefile (keep the .shx, .dbf and .prj
# files in the same folder).
SHP_PATH = str(Path(__file__).resolve().parent.parent / "dependencies" / "map_thing.shp")

NO_DATA_COLOR = "lightgrey"


# --------------------------------------------------
# 1. City-name matching: dataset names -> shapefile NAME_2
# --------------------------------------------------

# Spelling differences that cannot be fixed by stripping
# "Kab." / "Kota". Keys are (kind, normalised base name).
# The value is the exact NAME_2 used in the shapefile.
_ALIASES_RAW = {
    ("kab", "Aceh Pidie"): "Pidie",
    ("kab", "Bireun"): "Bireuen",
    ("kab", "Batubara"): "Batu Bara",
    ("kab", "Dharmas Raya"): "Dharmasraya",
    ("kab", "Fak-Fak"): "Fakfak",
    ("kab", "Karang Asem"): "Karangasem",
    ("kab", "Kota Waringin Barat"): "Kotawaringin Barat",
    ("kab", "Kota Waringin Timur"): "Kotawaringin Timur",
    ("kab", "Kutai Kertanegara"): "Kutai Kartanegara",
    ("kab", "Labuhan Batu"): "Labuhanbatu",
    ("kab", "Labuhan Batu Selatan"): "Labuhanbatu Selatan",
    ("kab", "Labuhan Batu Utara"): "Labuhanbatu Utara",
    ("kab", "Muko Muko"): "Mukomuko",
    ("kab", "Musi Banyu Asin"): "Musi Banyuasin",
    ("kab", "OKU Selatan"): "Ogan Komering Ulu Selatan",
    ("kab", "OKU Timur"): "Ogan Komering Ulu Timur",
    ("kab", "PakPak Bharat"): "Pakpak Barat",
    ("kab", "Peg. Bintang"): "Pegunungan Bintang",
    ("kab", "Tanjung Jabung Barat"): "Tanjung Jabung B",
    ("kab", "Tanjung Jabung Timur"): "Tanjung Jabung T",
    ("kab", "Tulang Bawang"): "Tulangbawang",
    # Kabupaten Mempawah is listed as "Pontianak" in GADM
    ("kab", "Mempawah"): "Pontianak",
    ("kota", "Bau Bau"): "Bau-Bau",
    ("kota", "Bukit Tinggi"): "Bukittinggi",
    ("kota", "Gunung Sitoli"): "Gunungsitoli",
    ("kota", "Lubuk Linggau"): "Lubuklinggau",
    ("kota", "Padang Sidimpuan"): "Padangsidimpuan",
    ("kota", "Pagaralam"): "Pagar Alam",
    ("kota", "Palangkaraya"): "Palangka Raya",
    ("kota", "Pangkal Pinang"): "Pangkalpinang",
    ("kota", "Pare-Pare"): "Parepare",
    ("kota", "Pematang Siantar"): "Pematangsiantar",
    ("kota", "Sawah Lunto"): "Sawahlunto",
    ("kota", "Tanjung Balai"): "Kota Tanjungbalai",
    ("kota", "Tanjung Pinang"): "Tanjungpinang",
    ("kota", "Tebing Tinggi"): "Tebingtinggi",
    ("kota", "Banjarbaru"): "Banjar Baru",
}

_PREFIX_RE = re.compile(
    r"^\s*(?:(kab(?:upaten)?)\b[.:]?\s*|(kota)\b[.:]?\s*)",
    flags=re.IGNORECASE,
)


def _key(text):
    """Lower-case and drop everything except letters and digits."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


_ALIASES = {
    (kind, _key(base)): target
    for (kind, base), target in _ALIASES_RAW.items()
}


def _split_name(raw):
    """Return (kind, base) from a dataset name such as 'Kab. Aceh Barat'."""
    text = str(raw).split("/")[0].strip()  # 'Kab. A/Kab. B' -> 'Kab. A'

    match = _PREFIX_RE.match(text)

    if match:
        kind = "kota" if match.group(2) else "kab"
        base = text[match.end():].strip()
    else:
        # No prefix, e.g. 'Kotamobagu'
        kind = "kab"
        base = text

    return kind, base


def match_city_names(names, shp_names, fuzzy_cutoff=0.90):
    """
    Match dataset city names to shapefile NAME_2 values.

    Returns a DataFrame with the columns:
        nama_kota, shp_name, method
    where method is one of: exact, alias, fuzzy, duplicate, unmatched.

    Regencies are matched before cities, so when a Kota and a Kab share
    one shapefile polygon (e.g. 'Banjar'), the regency keeps it and the
    city is reported as 'duplicate'.
    """
    shp_by_key = {_key(n): n for n in shp_names}

    def resolve(raw):
        kind, base = _split_name(raw)

        alias = _ALIASES.get((kind, _key(base)))
        if alias and _key(alias) in shp_by_key:
            return shp_by_key[_key(alias)], "alias"

        candidates = []
        if kind == "kota":
            candidates.append(_key("Kota " + base))
        candidates.append(_key(base))

        for cand in candidates:
            if cand in shp_by_key:
                return shp_by_key[cand], "exact"

        close = difflib.get_close_matches(
            _key(base), list(shp_by_key), n=1, cutoff=fuzzy_cutoff
        )
        if close:
            return shp_by_key[close[0]], "fuzzy"

        return None, "unmatched"

    rows = []
    taken = set()

    # Regencies first, cities second
    ordered = sorted(
        enumerate(names),
        key=lambda item: (_split_name(item[1])[0] == "kota", item[0]),
    )

    resolved = {}

    for idx, raw in ordered:
        target, method = resolve(raw)

        if target is not None and target in taken:
            target, method = None, "duplicate"
        elif target is not None:
            taken.add(target)

        resolved[idx] = (target, method)

    for idx, raw in enumerate(names):
        target, method = resolved[idx]
        rows.append({
            "nama_kota": raw,
            "shp_name": target,
            "method": method,
        })

    return pd.DataFrame(rows)


# --------------------------------------------------
# 2. Shapefile loading
# --------------------------------------------------

def load_shapefile(path=SHP_PATH):
    """
    Read the shapefile and dissolve it by NAME_2, as in the notebook.
    Wrap this with st.cache_resource in the page so it only runs once.
    """
    gdf = gpd.read_file(path)
    return gdf.dissolve(by="NAME_2").reset_index()


# --------------------------------------------------
# 3. Map
# --------------------------------------------------

# Colour-blind-friendly palette (Okabe-Ito order), then tab20 as fallback.
_PALETTE = [
    "#D55E00", "#0072B2", "#009E73", "#E69F00",
    "#CC79A7", "#56B4E9", "#F0E442", "#999999",
]


def _cluster_colors(cluster_ids):
    if len(cluster_ids) <= len(_PALETTE):
        return dict(zip(cluster_ids, _PALETTE))

    cmap = plt.get_cmap("tab20")
    return {
        cid: cmap(i % 20)
        for i, cid in enumerate(cluster_ids)
    }


def find_name_column(df):
    for col in df.columns:
        if _key(col) == "namakota":
            return col
    raise ValueError(
        "Could not find the city-name column. Expected "
        "'nama_kota' or 'Nama Kota'."
    )


def build_cluster_map(gdf_base, clustered_df, name_col=None):
    """
    Colour every shapefile region by its cluster.

    Returns:
        fig: matplotlib figure
        match_df: how each dataset name was matched
        no_data_regions: shapefile regions without a cluster (grey)
    """
    name_col = name_col or find_name_column(clustered_df)

    match_df = match_city_names(
        clustered_df[name_col].tolist(),
        gdf_base["NAME_2"].tolist(),
    )

    lookup = pd.DataFrame({
        "NAME_2": match_df["shp_name"].to_numpy(),
        "cluster": clustered_df["cluster"].to_numpy(),
    }).dropna(subset=["NAME_2"])

    gdf = gdf_base.merge(lookup, on="NAME_2", how="left")

    cluster_ids = sorted(gdf["cluster"].dropna().unique())
    colors = _cluster_colors(cluster_ids)

    gdf["color"] = gdf["cluster"].map(colors)
    gdf["color"] = gdf["color"].where(gdf["color"].notna(), NO_DATA_COLOR)

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    gdf.plot(
        ax=ax,
        color=gdf["color"].tolist(),
        alpha=0.7,
        edgecolor="black",
        linewidth=0.2,
    )

    counts = gdf["cluster"].value_counts()

    handles = [
        mpatches.Patch(
            color=colors[cid],
            alpha=0.7,
            label=f"Kelompok {int(cid)} ({counts.get(cid, 0)} wilayah)",
        )
        for cid in cluster_ids
    ]
    handles.append(
        mpatches.Patch(color=NO_DATA_COLOR, label="No data")
    )

    ax.legend(handles=handles, loc="upper right")
    ax.set_axis_off()
    fig.tight_layout()

    no_data_regions = gdf.loc[gdf["cluster"].isna(), "NAME_2"].tolist()

    return fig, match_df, no_data_regions