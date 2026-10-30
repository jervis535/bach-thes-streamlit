from datetime import datetime, timedelta, timezone

import streamlit as st

from services.admin import get_use_counts
from services.auth import require_admin

require_admin()

st.title("Jumlah penggunaan layanan")

st.divider()

today = datetime.now(timezone.utc).date()

picked = st.date_input(
    "Waktu",
    value=(today - timedelta(days=29), today),
    max_value=today,
    format="YYYY-MM-DD",
    help="Pilih tanggal awal dan tanggal akhir",
)

# While the admin is mid-selection, Streamlit returns only the start date.
if not isinstance(picked, tuple) or len(picked) != 2:
    st.info("Pilih tanggal akhir untuk lanjut")
    st.stop()

start, end = picked

try:
    with st.spinner("Menghitung jumlah penggunaan"):
        usage = get_use_counts(start, end)
except Exception as exc:
    st.error(f"Tidak bisa menghitung jumlah penggunaan: {exc}")
    st.stop()

total_clustering = int(usage["Clustering"].sum())
total_regression = int(usage["Panel Regression"].sum())

col1, col2, col3 = st.columns(3)
col1.metric("Jumlah penggunaan klasterisasi", f"{total_clustering:,}")
col2.metric("Jumlah penggunaan panel regression", f"{total_regression:,}")
col3.metric("Total jumlah penggunaan", f"{total_clustering + total_regression:,}")

if total_clustering + total_regression == 0:
    st.info("Tidak ada penggunaan di dalam waktu ini")

st.subheader("Penggunaan layanan per hari")
chart_df = usage.reset_index().melt(
    id_vars="Tanggal", var_name="Layanan", value_name="Jumlah"
)
st.bar_chart(chart_df, x="Tanggal", y="Jumlah", color="Layanan", stack=False)