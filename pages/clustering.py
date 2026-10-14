import streamlit as st
from components.sidebar import render_sidebar


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