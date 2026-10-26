import re

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from services.auth import require_role
from services.clustering import clustering, plot_cluster_profile_trends
from services.mapping import build_cluster_map, load_shapefile, SHP_PATH
from services.usage import record_use


@st.cache_resource
def get_shapefile():
    return load_shapefile(SHP_PATH)


require_role()

st.title("Clustering")
st.write("Upload your dataset and configure the number of clusters.")

st.divider()

# 1. File uploader
st.subheader("Upload Dataset")

uploaded_file = st.file_uploader(
    "Upload a .csv or .xlsx file",
    type=["csv", "xlsx"],
    accept_multiple_files=False,
    help="Only .csv and .xlsx files are accepted.",
)

# 2. Cluster range input
st.subheader("Cluster Configuration")

col1, col2 = st.columns(2)

with col1:
    min_clusters = st.number_input(
        "Minimum cluster amount",
        min_value=2,
        value=2,
        step=1,
    )

with col2:
    max_clusters = st.number_input(
        "Maximum cluster amount",
        min_value=2,
        value=10,
        step=1,
    )

# 3. Validate inputs
if min_clusters > max_clusters:
    st.error("The minimum number of clusters (X) cannot exceed the maximum (Y).")

# 4. Process the uploaded file
df = None

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()

        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)

        elif file_name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        else:
            st.error("Unsupported file format.")
            st.stop()

        st.success(f"File uploaded successfully: {uploaded_file.name}")

        st.subheader("Dataset Preview")
        st.dataframe(df.head(), use_container_width=True)

    except Exception as e:
        st.error(f"Could not read the uploaded file: {e}")


# Run clustering
st.divider()
st.subheader("Cluster analysis")

if min_clusters > max_clusters:
    st.error(
        "Minimum clusters cannot exceed maximum clusters."
    )
else:
    run_clustering = st.button(
        "Run Clustering",
        type="primary",
        use_container_width=True,
    )

    if run_clustering and df is None:
        st.warning("Please upload a dataset first.")

    elif run_clustering:
        try:
            with st.spinner(
                "running clustering process"
            ):

                results = clustering(
                    df,
                    int(min_clusters),
                    int(max_clusters),
                )

            record_use("clustering")

            st.success("Clustering completed successfully!")

            # 1. Evaluation metrics
            st.subheader("Cluster results")

            metrics_df = results["metrics_df"]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Best k (combined score)",
                    results["best_k"],
                )

            with col2:
                st.metric(
                    "Best Silhouette k",
                    results["best_silhouette_k"],
                )

            with col3:
                st.metric(
                    "Best DBI k",
                    results["best_dbi_k"],
                )

            st.caption(
                f"Combined score = {results['alpha']:.0%} normalized "
                f"Silhouette + {1 - results['alpha']:.0%} inverted "
                "normalized DBI. The final clusters use the k with "
                "the highest combined score."
            )

            st.dataframe(
                metrics_df.round(4),
                use_container_width=True,
                hide_index=True,
            )

            # 2. Evaluation plots
            st.subheader("Metric plots")
            st.pyplot(results["fig"])
            plt.close(results["fig"])

            # 3. Cluster distribution plot
            st.subheader("Cluster distribution")
            st.pyplot(results["fig_cluster"])
            plt.close(results["fig_cluster"])

            # 4. Silhouette plot (separate figure)
            st.subheader("Silhouette plot")
            st.pyplot(results["fig_silhouette"])
            plt.close(results["fig_silhouette"])

            # 5. Clustered dataset
            st.subheader("Clustered Dataset")

            clustered_df = results["clustered_df"]

            st.write(
                "**Rows after cleaning:**",
                len(clustered_df),
            )

            st.write(
                "**Cluster distribution:**"
            )

            distribution = (
                clustered_df["cluster"]
                .value_counts()
                .sort_index()
                .rename_axis("Cluster")
                .reset_index(name="Number of rows")
            )

            st.dataframe(
                distribution,
                use_container_width=True,
                hide_index=True,
            )

            # 6. Download results
            csv_data = clustered_df.to_csv(
                index=False
            ).encode("utf-8")

            # 7. Cluster Profile
            st.subheader("Cluster Profile")
            st.caption("Mean value per cluster for each year.")
 
            profile_fig = plot_cluster_profile_trends(clustered_df)
 
            if profile_fig is None:
                st.warning("No yearly variable columns were found.")
            else:
                st.pyplot(profile_fig)
                plt.close(profile_fig)
 
            st.subheader("Cluster Map")
            try:
                map_fig, match_df, no_data = build_cluster_map(
                    get_shapefile(), clustered_df
                )
                st.pyplot(map_fig)
                plt.close(map_fig)
 
                problems = match_df[match_df["method"].isin(["unmatched", "duplicate"])]
                if not problems.empty:
                    with st.expander(f"{len(problems)} cities could not be drawn"):
                        st.dataframe(
                            problems[["nama_kota", "method"]],
                            hide_index=True,
                            use_container_width=True,
                        )
            except Exception as e:
                st.warning(f"Could not draw the map: {e}")

        except Exception as e:
            st.error(
                f"Clustering failed: {e}"
            )