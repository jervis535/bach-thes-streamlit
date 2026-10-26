from datetime import datetime, timedelta, timezone

import streamlit as st

from services.admin import daily_signup_counts, get_signups
from services.auth import require_admin

require_admin()

st.title("Jumlah registrasi pengguna")

st.divider()

today = datetime.now(timezone.utc).date()

picked = st.date_input(
    "Waktu",
    value=(today - timedelta(days=29), today),
    max_value=today,
    format="YYYY-MM-DD",
    help="Pilih tanggal akhir untuk lanjut",
)

# While the admin is mid-selection, Streamlit returns only the start date.
if not isinstance(picked, tuple) or len(picked) != 2:
    st.info("")
    st.stop("Pilih tanggal akhir untuk lanjut")

start, end = picked

try:
    with st.spinner("Menghitung jumlah registrasi"):
        signups = get_signups(start, end)
except Exception as exc:
    st.error(f"Tidak bisa menghitung jumlah registrasi: {exc}")
    st.stop()

total = len(signups)
confirmed = int(signups["confirmed"].sum()) if total else 0

col1, col2, col3 = st.columns(3)
col1.metric("Jumlah Registrasi", f"{total:,}")
col2.metric("Email yang sudah konfirmasi", f"{confirmed:,}")
col3.metric("Email yang belom konfirmasi", f"{total - confirmed:,}")

if total == 0:
    st.info("tidak ada pengguna yang registrasi di dalam waktu ini")

st.subheader("Registrations per day")
st.bar_chart(daily_signup_counts(signups, start, end))