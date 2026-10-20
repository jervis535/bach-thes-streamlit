import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import RobustScaler


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
# 3. PCA + K-Means clustering and evaluation
# --------------------------------------------------

def clustering(df, kmin, kmax):
    """
    Run clustering on an uploaded DataFrame.

    Returns:
        transformed_df: transformed dataset
        clustered_df: dataset with cluster labels
        pca_summary: PCA information per variable group
        metrics_df: clustering evaluation metrics
        fig: DBI and Silhouette plots
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

        # A one-column group already has at most one component.
        # PCA is still applied to preserve the workflow.
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

    # Silhouette requires at least 2 clusters and fewer
    # clusters than samples.
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

    # H. Plot the evaluation metrics
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

    # I. Select the best candidates according to each metric
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

    # Return labels for the best Silhouette candidate
    clustered_df = cleaned_df.copy()
    clustered_df["cluster"] = labels_by_k[best_silhouette_k]

    return {
        "transformed_df": transformed_df,
        "clustered_df": clustered_df,
        "pca_summary": pca_summary,
        "metrics_df": metrics_df,
        "pca_features": X_pca,
        "pca_models": pca_models,
        "scalers": scalers,
        "models": models_by_k,
        "best_silhouette_k": best_silhouette_k,
        "best_dbi_k": best_dbi_k,
        "fig": fig,
    }