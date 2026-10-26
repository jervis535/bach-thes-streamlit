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

st.title("Klasterisasi")
st.write("Mengunggah datasetmu dan mulai proses klasterisasi")

st.divider()

# 1. File uploader
st.subheader("Unggah dataset")

uploaded_file = st.file_uploader(
    "Unggah file .csv atau .xlsx",
    type=["csv","xlsx"],
    accept_multiple_files=False,
    help="Hanya file .csv atau .xlsx akan diterima",
)

# 2. Cluster range input
st.subheader("Konfigurasi jumlah kelompok")

col1, col2 = st.columns(2)

with col1:
    min_clusters = st.number_input(
        "Jumlah kelompok minimum",
        min_value=2,
        value=2,
        step=1,
    )

with col2:
    max_clusters = st.number_input(
        "Jumlah kelompok maksimum",
        min_value=2,
        value=10,
        step=1,
    )

# 3. Validate inputs
if min_clusters > max_clusters:
    st.error("Jumlah kelompok minimum tidak bisa lebih dari jumlah kelompok maksimum")

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
            st.error("Format file salah harap unggah format .csv atau .xlsx")
            st.stop()

        st.success(f"File {uploaded_file.name} berhasil diunggah")
        st.dataframe(df.head(), use_container_width=True)

    except Exception as e:
        st.error(f"Could not read the uploaded file: {e}")


# Run clustering
st.divider()
st.subheader("Analisis kelompok")

if min_clusters > max_clusters:
    st.error(
        "Jumlah kelompok minimum tidak bisa lebih dari jumlah kelompok maksimum"
    )
else:
    run_clustering = st.button(
        "Mulai klasterisasi",
        type="primary",
        use_container_width=True,
    )

    if run_clustering and df is None:
        st.warning("Unggah dataset dulu sebelom memulai")

    elif run_clustering:
        try:
            with st.spinner(
                "Melakukan proses klasterisasi"
            ):

                results = clustering(
                    df,
                    int(min_clusters),
                    int(max_clusters),
                )

            record_use("clustering")

            st.success("Klasterisasi berhasil")

            # 1. Evaluation metrics
            st.subheader("Hasil klasterisasi")

            metrics_df = results["metrics_df"]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Jumlah K paling baik",
                    results["best_k"],
                )

            with col2:
                st.metric(
                    "Jumlah K dengan silhouette tertinggi",
                    results["best_silhouette_k"],
                )

            with col3:
                st.metric(
                    "Jumlah K dengan DBI tertinggi",
                    results["best_dbi_k"],
                )

            st.dataframe(
                metrics_df[["k","silhouette_score","davies_bouldin_index"]].round(4),
                use_container_width=True,
                hide_index=True,
            )

            # 2. Evaluation plots
            st.subheader("Grafik untuk metrik")
            st.pyplot(results["fig"])
            plt.close(results["fig"])

            # 3. Cluster distribution plot
            st.subheader("Distribusi kelompok")
            st.pyplot(results["fig_cluster"])
            plt.close(results["fig_cluster"])

            # 4. Silhouette plot (separate figure)
            st.subheader("grafik untuk silhouette")
            st.pyplot(results["fig_silhouette"])
            plt.close(results["fig_silhouette"])

            # 5. Clustered dataset
            st.subheader("Clustered Dataset")

            clustered_df = results["clustered_df"]

            st.write(
                "Jumlah wilayah yang ada penghasilan:",
                len(clustered_df),
            )

            distribution = (
                clustered_df["cluster"]
                .value_counts()
                .sort_index()
                .rename_axis("Kelompok")
                .reset_index(name="Jumlah wilayah")
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
            st.subheader("Profile kelompok")
            st.caption("(Rata-rata setiap variabel)")
 
            profile_fig = plot_cluster_profile_trends(clustered_df)
 
            if profile_fig is None:
                st.warning("No yearly variable columns were found.")
            else:
                st.pyplot(profile_fig)
                plt.close(profile_fig)
 
            st.subheader("Peta kelompok")
            try:
                map_fig, match_df, no_data = build_cluster_map(
                    get_shapefile(), clustered_df
                )
                st.pyplot(map_fig)
                plt.close(map_fig)
 
                problems = match_df[match_df["method"].isin(["unmatched", "duplicate"])]
            except Exception as e:
                st.warning(f"Tidak bisa gambar peta: {e}")

        except Exception as e:
            st.error(
                f"Klasterisasi gagal: {e}"
            )