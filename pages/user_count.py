from datetime import datetime, timedelta, timezone

import streamlit as st

from services.admin import daily_signup_counts, get_signups
from services.auth import require_admin

require_admin()

st.title("👥 Registered users")
st.write("Accounts created in the selected time frame.")

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
    with st.spinner("Loading registrations"):
        signups = get_signups(start, end)
except Exception as exc:
    st.error(f"Could not load registrations: {exc}")
    st.stop()

total = len(signups)
confirmed = int(signups["confirmed"].sum()) if total else 0

col1, col2, col3 = st.columns(3)
col1.metric("New registrations", f"{total:,}")
col2.metric("Email confirmed", f"{confirmed:,}")
col3.metric("Not confirmed yet", f"{total - confirmed:,}")

if total == 0:
    st.info("Nobody registered in this time frame.")

st.subheader("Registrations per day")
st.bar_chart(daily_signup_counts(signups, start, end))