import streamlit as st
from components.sidebar import render_sidebar
from services.clustering import clustering
from services.mapping import build_cluster_map, load_shapefile, SHP_PATH
import re

@st.cache_resource
def get_shapefile():
    return load_shapefile(SHP_PATH)



st.set_page_config(
    page_title="Clustering",
    page_icon="📊",
    layout="wide",
)

render_sidebar()

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
    min_clusters=st.number_input(
        "Minimum cluster amount",
        min_value=2,
        value=2,
        step=1,
    )

with col2:
    max_clusters=st.number_input(
        "Maximum cluster amount",
        min_value=2,
        value=10,
        step=1,
    )

# 3. Validate inputs
if min_clusters > max_clusters:
    st.error("The minimum number of clusters (X) cannot exceed the maximum (Y).")

# 4. Process the uploaded file
if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()

        if file_name.endswith(".csv"):
            import pandas as pd
            df = pd.read_csv(uploaded_file)

        elif file_name.endswith(".xlsx"):
            import pandas as pd
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

    if run_clustering:
        try:
            with st.spinner(
                "running clustering process"
            ):


                results = clustering(
                    df,
                    int(min_clusters),
                    int(max_clusters),
                )

            st.success("Clustering completed successfully!")

            # 1. Evaluation metrics
            st.subheader("Cluster results")

            metrics_df = results["metrics_df"]

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Best Silhouette k",
                    results["best_silhouette_k"],
                )

            with col2:
                st.metric(
                    "Best DBI k",
                    results["best_dbi_k"],
                )

            st.dataframe(
                metrics_df.round(4),
                use_container_width=True,
                hide_index=True,
            )

            # 2. Evaluation plots
            st.subheader("Metric plots")
            st.pyplot(results["fig"])
            import matplotlib.pyplot as plt
            plt.close(results["fig"])

            # 4. Clustered dataset
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

            # 5. Download results
            csv_data = clustered_df.to_csv(
                index=False
            ).encode("utf-8")



            # 4. Cluster Profile
            st.subheader("Cluster Profile")

            # Identify all columns containing yearly variables
            yearly_cols = [
                col for col in clustered_df.columns
                if re.search(r"\s+\d{4}$", str(col))
            ]

            # Group columns by variable name
            variable_groups = {}

            for col in yearly_cols:
                variable_name = re.sub(
                    r"\s+\d{4}$", "", str(col)
                ).strip()

                variable_groups.setdefault(
                    variable_name, []
                ).append(col)

            if not variable_groups:
                st.warning("No yearly variable columns were found.")

            else:
                # Stage 1: Calculate each city's average across years
                row_profiles = pd.DataFrame(
                    index=clustered_df.index
                )

                for variable_name, cols in variable_groups.items():
                    yearly_values = clustered_df[cols].apply(
                        pd.to_numeric,
                        errors="coerce",
                    )

                    row_profiles[variable_name] = (
                        yearly_values.mean(axis=1)
                    )

                # Attach cluster labels to each city's profile
                row_profiles["cluster"] = (
                    clustered_df["cluster"].to_numpy()
                )

                # Stage 2: Calculate average profiles for each cluster
                cluster_profile = (
                    row_profiles
                    .groupby("cluster", sort=True)
                    .mean(numeric_only=True)
                    .T
                )

                # Prepare the table for display
                cluster_profile.index.name = "Variable"

                cluster_profile.columns = [
                    f"Cluster {cluster_id}"
                    for cluster_id in cluster_profile.columns
                ]

                cluster_profile = (
                    cluster_profile
                    .reset_index()
                    .round(4)
                )

                st.write(
                    "All variables here are averaged over the years"
                )

                st.dataframe(
                    cluster_profile,
                    use_container_width=True,
                    hide_index=True,
                )
                
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
        