import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)
from sklearn.preprocessing import RobustScaler
import math


# --------------------------------------------------
# 1. Remove rows where agricultural variables are zero
# --------------------------------------------------

def remove_0(df):
    """
    Remove rows where all luas, produksi, and produktivitas
    columns contain zero or NaN.

    Accepts a pandas DataFrame directly.
    """
    df = df.copy()

    cols = [
        c for c in df.columns
        if c.split()[0] in ("luas", "produksi", "produktivitas")
    ]

    if not cols:
        return df

    values = df[cols].apply(pd.to_numeric, errors="coerce")
    all_zero = values.fillna(0).eq(0).all(axis=1)

    return df.loc[~all_zero].reset_index(drop=True)


# --------------------------------------------------
# 2. Transform the dataset
# --------------------------------------------------

def clustering_transformation(df):
    """
    Transform agricultural variables using log1p and
    weather variables using RobustScaler.

    Accepts and returns DataFrames. No intermediate CSV
    files are created.
    """
    df_transformed = df.copy()

    log_groups = [
        "luas",
        "produksi",
        "produktivitas",
    ]

    robust_groups = [
        "humidity_avg",
        "wind_avg",
        "rainfall_mm",
        "wind_max",
        "temp_min",
        "temp_max",
        "temp_avg",
    ]

    scalers = {}

    def get_cols(group):
        return [
            c for c in df_transformed.columns
            if c.startswith(group + " ")
        ]

    # Log transformation for agricultural variables
    for group in log_groups:
        cols = get_cols(group)

        if not cols:
            continue

        data = df_transformed[cols].apply(
            pd.to_numeric, errors="coerce"
        )

        if data.lt(0).any().any():
            raise ValueError(
                f"Negative values found in '{group}'. "
                "The log1p transformation requires values >= 0."
            )

        df_transformed[cols] = np.log1p(data)
        scalers[group] = "log1p"

    # Robust scaling for weather variables.
    # Pool all years of each variable, as in the notebook.
    for group in robust_groups:
        cols = get_cols(group)

        if not cols:
            continue

        data = df_transformed[cols].apply(
            pd.to_numeric, errors="coerce"
        )

        scaler = RobustScaler()
        pooled = data.to_numpy().reshape(-1, 1)

        valid = np.isfinite(pooled[:, 0])

        if not valid.any():
            raise ValueError(
                f"Variable '{group}' contains no valid numeric values."
            )

        scaler.fit(pooled[valid])

        transformed = np.full(pooled.shape, np.nan, dtype=float)
        transformed[valid] = scaler.transform(pooled[valid])

        df_transformed[cols] = transformed.reshape(data.shape)
        scalers[group] = scaler

    return df_transformed, scalers


# --------------------------------------------------
# 3. Helpers: metric normalization and plots
# --------------------------------------------------

def _min_max(series):
    """Min-max normalize a Series to 0-1 (constant series -> 0)."""
    span = series.max() - series.min()

    if span == 0:
        return pd.Series(0.0, index=series.index)

    return (series - series.min()) / span


def plot_cluster_distribution(X_pca, labels, k):
    """
    Scatter plot of the clusters using the first two
    principal components (figure 1 of the two cluster plots).
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    x = X_pca[:, 0]
    y = X_pca[:, 1] if X_pca.shape[1] > 1 else np.zeros(len(x))

    scatter = ax.scatter(
        x,
        y,
        c=labels,
        cmap="viridis",
        s=50,
        alpha=0.7,
    )

    ax.set_xlabel("Principal Component 1")
    ax.set_ylabel(
        "Principal Component 2"
        if X_pca.shape[1] > 1
        else "(only one component available)"
    )
    ax.set_title(f"K-Means Cluster Distribution (k={k})")

    ax.legend(
        *scatter.legend_elements(),
        title="Cluster",
    )

    ax.grid(alpha=0.2)
    fig.tight_layout()

    return fig


def plot_silhouette(X_pca, labels, k):
    """
    Silhouette plot for the chosen k (figure 2 of the two
    cluster plots). Shows the per-sample silhouette values of
    each cluster and the average score as a red dashed line.
    """
    sample_values = silhouette_samples(X_pca, labels)
    avg_score = silhouette_score(X_pca, labels)

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.set_xlim([-0.1, 1])
    # Extra space between clusters so they are visually separated
    ax.set_ylim([0, len(X_pca) + (k + 1) * 10])

    y_lower = 10

    for i in range(k):
        cluster_values = np.sort(sample_values[labels == i])

        size = cluster_values.shape[0]
        y_upper = y_lower + size

        color = cm.nipy_spectral(float(i) / k)

        ax.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            cluster_values,
            facecolor=color,
            edgecolor=color,
            alpha=0.7,
        )

        # Cluster label in the middle of each silhouette
        ax.text(-0.05, y_lower + 0.5 * size, str(i))

        y_lower = y_upper + 10

    ax.axvline(x=avg_score, color="red", linestyle="--")

    ax.set_title("The silhouette plot for the various clusters.")
    ax.set_xlabel("The silhouette coefficient values")
    ax.set_ylabel("Cluster label")
    ax.set_yticks([])
    ax.set_xticks([-0.1, 0, 0.2, 0.4, 0.6, 0.8, 1])

    fig.suptitle(
        f"Silhouette analysis for KMeans clustering "
        f"with n_clusters = {k}",
        fontsize=12,
        fontweight="bold",
    )

    fig.tight_layout()

    return fig


# --------------------------------------------------
# 4. PCA + K-Means clustering and evaluation
# --------------------------------------------------

def clustering(df, kmin, kmax, alpha=0.5):
    """
    Run clustering on an uploaded DataFrame.

    alpha is the weight of the Silhouette score in the combined
    score (1 - alpha is the weight of the DBI).

    Returns a dict with:
        transformed_df: transformed dataset
        clustered_df: dataset with cluster labels
        pca_summary: PCA information per variable group
        metrics_df: metrics per k, including the combined score
        fig: DBI and Silhouette metric plots
        fig_cluster: cluster distribution scatter plot
        fig_silhouette: silhouette plot for the best k
    """

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    if kmin < 2 or kmax < kmin:
        raise ValueError(
            "Cluster range must satisfy 2 <= kmin <= kmax."
        )

    # A. Clean and transform the uploaded dataset
    cleaned_df = remove_0(df)

    if cleaned_df.empty:
        raise ValueError(
            "No rows remain after removing zero-valued "
            "agricultural observations."
        )

    transformed_df, scalers = clustering_transformation(
        cleaned_df
    )

    # B. Exclude metadata and identify year-based features
    exclude_cols = {
        "nama_kota",
        "latitude",
        "longitude",
        "era5_latitude",
        "era5_longitude",
        "distance_km",
    }

    feature_cols = [
        c for c in transformed_df.columns
        if c not in exclude_cols
        and re.search(r"\s+\d{4}$", str(c))
    ]

    if not feature_cols:
        raise ValueError(
            "No yearly feature columns were found. "
            "Expected names such as 'luas 2020' or "
            "'temp_avg 2020'."
        )

    # C. Group yearly columns by variable name
    var_groups = {}

    for col in feature_cols:
        var_name = re.sub(r"\s*\d{4}$", "", col).strip()
        var_groups.setdefault(var_name, []).append(col)

    # D. Convert features to numeric and impute missing values
    X_df = transformed_df[feature_cols].apply(
        pd.to_numeric, errors="coerce"
    )

    X_df = X_df.replace([np.inf, -np.inf], np.nan)

    # Remove columns with no valid numeric values
    X_df = X_df.dropna(axis=1, how="all")

    if X_df.empty or X_df.shape[1] == 0:
        raise ValueError(
            "No usable numeric clustering features were found."
        )

    feature_cols = list(X_df.columns)

    # Update groups after removing unusable columns
    var_groups = {}

    for col in feature_cols:
        var_name = re.sub(r"\s*\d{4}$", "", col).strip()
        var_groups.setdefault(var_name, []).append(col)

    imputer = SimpleImputer(strategy="median")
    X_imputed = pd.DataFrame(
        imputer.fit_transform(X_df),
        columns=feature_cols,
        index=X_df.index,
    )

    # E. Apply PCA independently to each variable group
    pca_parts = []
    pca_models = {}
    summary = []

    for var_name, cols in var_groups.items():
        group_data = X_imputed[cols].to_numpy()

        n_components = min(
            group_data.shape[0],
            group_data.shape[1],
        )

        if n_components < 1:
            continue

        pca_var = PCA(
            n_components=0.90,
            svd_solver="full",
        )

        scores = pca_var.fit_transform(group_data)

        pca_models[var_name] = pca_var
        pca_parts.append(scores)

        summary.append({
            "variable": var_name,
            "n_original": len(cols),
            "n_components": pca_var.n_components_,
            "variance_explained": (
                pca_var.explained_variance_ratio_.sum()
            ),
        })

    if not pca_parts:
        raise ValueError(
            "PCA could not generate any components."
        )

    X_pca = np.hstack(pca_parts)

    pca_summary = pd.DataFrame(summary)

    # F. Validate the requested cluster range
    n_samples = X_pca.shape[0]

    valid_k = [
        k for k in range(int(kmin), int(kmax) + 1)
        if 2 <= k < n_samples
    ]

    if not valid_k:
        raise ValueError(
            f"Cannot evaluate the requested cluster range "
            f"{kmin}-{kmax} with {n_samples} rows. "
            "At least 3 rows are required, and each evaluated "
            "cluster count must be smaller than the row count."
        )

    # G. Run K-Means and calculate evaluation metrics
    results = []
    labels_by_k = {}
    models_by_k = {}

    for k in valid_k:
        km = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10,
        )

        labels = km.fit_predict(X_pca)

        sil = silhouette_score(X_pca, labels)
        dbi = davies_bouldin_score(X_pca, labels)

        results.append({
            "k": k,
            "silhouette_score": sil,
            "davies_bouldin_index": dbi,
        })

        labels_by_k[k] = labels
        models_by_k[k] = km

    metrics_df = pd.DataFrame(results)

    # H. Combined score (Silhouette: higher is better,
    #    DBI: lower is better)
    metrics_df["silhouette_norm"] = _min_max(
        metrics_df["silhouette_score"]
    )
    metrics_df["dbi_norm"] = _min_max(
        metrics_df["davies_bouldin_index"]
    )

    metrics_df["combined_score"] = (
        alpha * metrics_df["silhouette_norm"]
        + (1 - alpha) * (1 - metrics_df["dbi_norm"])
    )

    # I. Plot the evaluation metrics
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(
        metrics_df["k"],
        metrics_df["davies_bouldin_index"],
        marker="o",
        color="blue",
    )
    axes[0].set_title("Davies-Bouldin Index")
    axes[0].set_xlabel("Number of clusters (k)")
    axes[0].set_ylabel("DBI")
    axes[0].grid(alpha=0.3)

    axes[1].plot(
        metrics_df["k"],
        metrics_df["silhouette_score"],
        marker="o",
        color="orange",
    )
    axes[1].set_title("Silhouette Score")
    axes[1].set_xlabel("Number of clusters (k)")
    axes[1].set_ylabel("Silhouette")
    axes[1].grid(alpha=0.3)

    fig.tight_layout()

    # J. Select the best k
    best_row = metrics_df.loc[metrics_df["combined_score"].idxmax()]
    best_k = int(best_row["k"])

    best_silhouette_k = int(
        metrics_df.loc[
            metrics_df["silhouette_score"].idxmax(), "k"
        ]
    )

    best_dbi_k = int(
        metrics_df.loc[
            metrics_df["davies_bouldin_index"].idxmin(), "k"
        ]
    )

    # K. Final clustering uses the best combined-score k
    final_labels = labels_by_k[best_k]

    clustered_df = cleaned_df.copy()
    clustered_df["cluster"] = final_labels

    # L. Two separate plots for the final clustering
    fig_cluster = plot_cluster_distribution(
        X_pca, final_labels, best_k
    )
    fig_silhouette = plot_silhouette(
        X_pca, final_labels, best_k
    )

    return {
        "transformed_df": transformed_df,
        "clustered_df": clustered_df,
        "pca_summary": pca_summary,
        "metrics_df": metrics_df,
        "pca_features": X_pca,
        "pca_models": pca_models,
        "scalers": scalers,
        "models": models_by_k,
        "best_k": best_k,
        "best_combined_score": float(best_row["combined_score"]),
        "best_silhouette_k": best_silhouette_k,
        "best_dbi_k": best_dbi_k,
        "alpha": alpha,
        "fig": fig,
        "fig_cluster": fig_cluster,
        "fig_silhouette": fig_silhouette,
    }

_UNITS = {
    "rainfall_mm": "mm",
    "temp_min": "°C",
    "temp_max": "°C",
    "temp_avg": "°C",
}
 
_BASE_COLORS = ["blue", "red", "limegreen"]
 
 
def _cluster_colors(n):
    """Blue / red / green like the reference chart, tab10 beyond that."""
    if n <= len(_BASE_COLORS):
        return _BASE_COLORS[:n]
    extra = plt.cm.tab10(np.linspace(0, 1, 10))
    return [extra[i % 10] for i in range(n)]
 
 
def plot_cluster_profile_trends(clustered_df, ncols=3):
    """
    One subplot per variable: x = year, y = mean value of the
    cities in each cluster, one line per cluster.
 
    Uses the original (untransformed) values in clustered_df.
    Returns a matplotlib Figure, or None if no yearly columns exist.
    """
    year_re = re.compile(r"^(?P<var>.+?)\s+(?P<year>\d{4})$")
 
    # variable name -> {year: column name}
    groups = {}
    for col in clustered_df.columns:
        m = year_re.match(str(col).strip())
        if m:
            groups.setdefault(m["var"], {})[int(m["year"])] = col
 
    if not groups:
        return None
 
    cluster_ids = sorted(clustered_df["cluster"].unique())
    colors = _cluster_colors(len(cluster_ids))
 
    n_vars = len(groups)
    nrows = math.ceil(n_vars / ncols)
 
    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(5.5 * ncols, 3.8 * nrows),
        squeeze=False,
    )
    axes = axes.ravel()
 
    for ax, (var, year_cols) in zip(axes, groups.items()):
        years = sorted(year_cols)
 
        data = clustered_df[[year_cols[y] for y in years]].apply(
            pd.to_numeric, errors="coerce"
        )
        data.columns = years
        data["cluster"] = clustered_df["cluster"].to_numpy()
 
        means = data.groupby("cluster").mean()
 
        for color, cid in zip(colors, cluster_ids):
            ax.plot(
                years,
                means.loc[cid, years],
                marker="o",
                markersize=3,
                linewidth=1.5,
                color=color,
                label=f"Cluster {cid}",
            )
 
        ax.set_title(var.replace("_", " ").title())
        ax.set_xlabel("Year")
        ax.set_ylabel(_UNITS.get(var, "Mean value"))
        ax.set_xticks(years)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
 
    # hide unused panels in the last row
    for ax in axes[n_vars:]:
        ax.set_visible(False)
 
    fig.tight_layout()
    return fig
