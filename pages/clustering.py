import streamlit as st
from components.sidebar import render_sidebar
from services.clustering import clustering


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
    "Choose a CSV or Excel file",
    type=["csv", "xlsx"],
    accept_multiple_files=False,
    help="Only .csv and .xlsx files are accepted.",
)

# 2. Cluster range input
st.subheader("Cluster Configuration")

col1, col2 = st.columns(2)

with col1:
    min_clusters=st.number_input(
        "Minimum number of clusters (X)",
        min_value=2,
        value=2,
        step=1,
    )

with col2:
    max_clusters=st.number_input(
        "Maximum number of clusters (Y)",
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

        st.write(f"**Rows:** {df.shape[0]}")
        st.write(f"**Columns:** {df.shape[1]}")

        if min_clusters <= max_clusters:
            st.write(
                f"**Cluster range:** {int(min_clusters)} to "
                f"{int(max_clusters)}"
            )

    except Exception as e:
        st.error(f"Could not read the uploaded file: {e}")


# Run clustering
st.divider()
st.subheader("Clustering Analysis")

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
                "Running data transformation, PCA, "
                "and K-Means clustering..."
            ):


                results = clustering(
                    df,
                    int(min_clusters),
                    int(max_clusters),
                )

            st.success("Clustering completed successfully!")

            # 1. Evaluation metrics
            st.subheader("Cluster Evaluation")

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
            st.subheader("Cluster Selection Plots")
            st.pyplot(results["fig"])
            import matplotlib.pyplot as plt
            plt.close(results["fig"])

            # 3. PCA summary
            st.subheader("PCA Summary")

            pca_summary = results["pca_summary"].copy()
            pca_summary["variance_explained"] *= 100

            st.dataframe(
                pca_summary.rename(columns={
                    "variable": "Variable",
                    "n_original": "Original Features",
                    "n_components": "PCA Components",
                    "variance_explained": "Variance Explained (%)",
                }).round(2),
                use_container_width=True,
                hide_index=True,
            )

            # 4. Clustered dataset
            st.subheader("Clustered Dataset")

            clustered_df = results["clustered_df"]

            st.dataframe(
                clustered_df,
                use_container_width=True,
            )

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

            st.download_button(
                "Download Clustered Dataset",
                data=csv_data,
                file_name="clustered_dataset.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(
                f"Clustering failed: {e}"
            )