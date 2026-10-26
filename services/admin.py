"""Admin-only data access. Every call is re-checked inside Postgres
(see admin_setup.sql), so these functions only work for admin accounts."""

from datetime import date

import pandas as pd

from services.auth import get_client

USAGE_COLUMNS = ["day", "clustering_count", "panel_regression_count"]
SIGNUP_COLUMNS = [
    "user_id",
    "email",
    "registered_at",
    "confirmed",
    "last_sign_in_at",
]


def _params(start: date, end: date) -> dict:
    return {"p_start": start.isoformat(), "p_end": end.isoformat()}


def get_use_counts(start: date, end: date) -> pd.DataFrame:
    """Daily use counts for every day in [start, end], zero-filled.

    Returns a DataFrame indexed by date with "Clustering" and
    "Panel Regression" columns.
    """
    res = get_client().rpc("admin_use_count", _params(start, end)).execute()

    df = pd.DataFrame(res.data or [], columns=USAGE_COLUMNS)
    df["day"] = pd.to_datetime(df["day"])

    full_range = pd.date_range(start, end, freq="D", name="Date")
    df = (
        df.set_index("day")
        .reindex(full_range, fill_value=0)
        .rename(
            columns={
                "clustering_count": "Clustering",
                "panel_regression_count": "Panel Regression",
            }
        )[["Clustering", "Panel Regression"]]
        .astype(int)
    )
    return df


def get_signups(start: date, end: date) -> pd.DataFrame:
    """Users who registered in [start, end], newest first."""
    res = get_client().rpc("admin_signups", _params(start, end)).execute()

    df = pd.DataFrame(res.data or [], columns=SIGNUP_COLUMNS)
    df["registered_at"] = pd.to_datetime(df["registered_at"], utc=True)
    df["last_sign_in_at"] = pd.to_datetime(df["last_sign_in_at"], utc=True)
    return df


def daily_signup_counts(signups: pd.DataFrame, start: date, end: date) -> pd.Series:
    """Registrations per UTC day for every day in [start, end], zero-filled."""
    full_range = pd.date_range(start, end, freq="D", name="Date")
    if signups.empty:
        return pd.Series(0, index=full_range, name="Registrations")

    per_day = (
        signups["registered_at"]
        .dt.tz_convert("UTC")
        .dt.tz_localize(None)
        .dt.normalize()
        .value_counts()
    )
    return (
        per_day.reindex(full_range, fill_value=0)
        .astype(int)
        .rename("Registrations")
    )