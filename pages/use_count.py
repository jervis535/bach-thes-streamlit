from datetime import datetime, timedelta, timezone

import streamlit as st

from services.admin import get_use_counts
from services.auth import require_admin

require_admin()

st.title("📊 Usage statistics")
st.write("How many times each service was used in the selected time frame.")

st.divider()

today = datetime.now(timezone.utc).date()

picked = st.date_input(
    "Time frame",
    value=(today - timedelta(days=29), today),
    max_value=today,
    format="YYYY-MM-DD",
    help="Pick a start and an end date. Days are counted in UTC.",
)

# While the admin is mid-selection, Streamlit returns only the start date.
if not isinstance(picked, tuple) or len(picked) != 2:
    st.info("Select an end date to continue.")
    st.stop()

start, end = picked

try:
    with st.spinner("Loading usage data"):
        usage = get_use_counts(start, end)
except Exception as exc:
    st.error(f"Could not load usage data: {exc}")
    st.stop()

total_clustering = int(usage["Clustering"].sum())
total_regression = int(usage["Panel Regression"].sum())

col1, col2, col3 = st.columns(3)
col1.metric("Clustering runs", f"{total_clustering:,}")
col2.metric("Panel regression runs", f"{total_regression:,}")
col3.metric("Total runs", f"{total_clustering + total_regression:,}")

if total_clustering + total_regression == 0:
    st.info("No usage was recorded in this time frame.")

st.subheader("Uses per day")
st.bar_chart(usage, y=["Clustering", "Panel Regression"], stack=False)