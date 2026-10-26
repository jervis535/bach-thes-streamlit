import re

import pandas as pd
import streamlit as st
from services.auth import require_role
from services.panel_regression import run_panel_regression
from services.usage import record_use


require_role()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# Matches "luas 2010", "temp_min 2015", "wind_avg_2024", ...
YEAR_SUFFIX = re.compile(r"^(?P<var>.+?)[\s_]*(?P<year>(?:19|20)\d{2})$")

DEP_KEY = "dependent_vars"
INDEP_KEY = "independent_vars"


def detect_columns(df):
    """Split the columns into time-varying variables and static columns.

    "luas 2010" ... "luas 2024" become one variable, "luas", with a
    {year: column_name} mapping. Everything else (nama_kota, latitude, ...)
    is a static column.
    """
    groups = {}
    for col in df.columns:
        match = YEAR_SUFFIX.match(str(col).strip())
        if match:
            groups.setdefault(match["var"], {})[int(match["year"])] = col

    # A "variable" needs at least 2 years to count as time-varying
    time_vars = {v: years for v, years in groups.items() if len(years) >= 2}
    grouped_cols = {c for years in time_vars.values() for c in years.values()}
    static_cols = [c for c in df.columns if c not in grouped_cols]
    return time_vars, static_cols


def pick_entity_column(df, static_cols):
    """The first non-numeric static column is treated as the entity ID."""
    for col in static_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return col
    return static_cols[0] if static_cols else df.columns[0]


def build_panel(df, entity_col, time_vars, selected):
    """Reshape the wide dataset into long panel format (entity x year).

    Time-varying variables are melted into rows; static variables are
    repeated for every year of the same entity.
    """
    work = df.reset_index(drop=True).copy()
    work["entity_id"] = work.index  # row number is a safe unique ID

    parts, static_selected = [], []
    for var in selected:
        if var in time_vars:
            col_by_year = time_vars[var]
            part = work[["entity_id", *col_by_year.values()]].rename(
                columns={col: year for year, col in col_by_year.items()}
            )
            part = part.melt(id_vars="entity_id", var_name="year", value_name=var)
            parts.append(part.set_index(["entity_id", "year"]))
        else:
            static_selected.append(var)

    if parts:
        panel = pd.concat(parts, axis=1).reset_index()
    else:  # only static variables selected
        panel = work[["entity_id"]].copy()

    if static_selected:
        panel = panel.merge(
            work[["entity_id", *static_selected]], on="entity_id", how="left"
        )

    panel.insert(1, entity_col, panel["entity_id"].map(work[entity_col]))
    sort_cols = ["entity_id", "year"] if "year" in panel.columns else ["entity_id"]
    return panel.sort_values(sort_cols).reset_index(drop=True)


def reset_result():
    st.session_state.pop("regression_config", None)
    st.session_state.pop("regression_results", None)


def add_variable(role):
    pick_key = f"pick_{role}"
    choice = st.session_state.get(pick_key)
    if choice and choice not in st.session_state[role]:
        st.session_state[role].append(choice)
    st.session_state[pick_key] = None  # clear the dropdown again
    reset_result()


def remove_variable(role, var):
    if var in st.session_state[role]:
        st.session_state[role].remove(var)
    reset_result()


def render_role(title, role, options):
    """One column: header, dropdown, and the selected variables with a red X."""
    with st.container(border=True):
        st.markdown(f"##### {title}")
        st.selectbox(
            "Click to select variables",
            options=options,
            index=None,
            placeholder="Click to select variables",
            key=f"pick_{role}",
            on_change=add_variable,
            args=(role,),
            label_visibility="collapsed",
        )
        for var in st.session_state[role]:
            name_col, btn_col = st.columns([5, 1])
            name_col.markdown(f"• {var}")
            btn_col.button(
                "✕",
                key=f"rm_{role}_{var}",
                type="primary",
                on_click=remove_variable,
                args=(role, var),
            )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.title("Panel Regression")
st.write("Mengunggah datasetmu dan menyesuaikan variabel bergantung dan tidak bergantung")

st.divider()

# 1. File uploader
st.subheader("Mengunggah dataset")

uploaded_file = st.file_uploader(
    "Unggah file .csv atau .xlsx",
    type=["csv","xlsx"],
    accept_multiple_files=False,
    help="Hanya file .csv atau .xlsx akan diterima",
)

# 2. Process the uploaded file
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

        st.dataframe(df.head(), use_container_width=True)

    except Exception as e:
        st.error(f"Could not read the uploaded file: {e}")
        st.stop()

    # 3. Detect variables
    time_vars, static_cols = detect_columns(df)
    entity_col = pick_entity_column(df, static_cols)
    static_numeric = [
        c
        for c in static_cols
        if c != entity_col and pd.api.types.is_numeric_dtype(df[c])
    ]
    all_vars = list(time_vars) + static_numeric

    # Start with empty selections whenever a different file is uploaded
    file_sig = f"{uploaded_file.name}-{uploaded_file.size}"
    if st.session_state.get("file_sig") != file_sig:
        st.session_state["file_sig"] = file_sig
        st.session_state[DEP_KEY] = []
        st.session_state[INDEP_KEY] = []
        reset_result()

    st.divider()
    st.subheader("Pilih variabel")

    if time_vars:
        years = sorted({y for ys in time_vars.values() for y in ys})
        st.caption(
            f"Detected {len(time_vars)} time-varying variables ({years[0]}–{years[-1]})"
        )
    if df[entity_col].duplicated().any():
        st.warning(
            f"'{entity_col}' has duplicate values, so each row is treated as its own entity."
        )

    # 4. Remaining variables
    chosen = set(st.session_state[DEP_KEY]) | set(st.session_state[INDEP_KEY])
    remaining = [v for v in all_vars if v not in chosen]

    st.markdown("##### Variabel sisa:")
    if remaining:
        grid = st.columns(4)
        for i, var in enumerate(remaining):
            grid[i % 4].markdown(f"• {var}")
    else:
        st.caption("Semua variabel sudah terpilih")

    # 5. Dependent / independent selectors
    left, right = st.columns(2, gap="large")
    with left:
        render_role("Variabel bergantung:", DEP_KEY, remaining)
    with right:
        render_role("Variabel tidak bergantung:", INDEP_KEY, remaining)

    # 6. OK button
    _, center, _ = st.columns([2, 1, 2])
    if center.button("OK", type="primary", use_container_width=True):
        dep = st.session_state[DEP_KEY]
        indep = st.session_state[INDEP_KEY]
        if not dep or not indep:
            st.warning("Select at least one dependent and one independent variable.")
        else:
            st.session_state["regression_config"] = {
                "dependent": list(dep),
                "independent": list(indep),
                "entity_col": entity_col,
                "panel": build_panel(df, entity_col, time_vars, dep + indep),
            }

    config = st.session_state.get("regression_config")
    if config:

        if st.button(
            "Mulai panel regression",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Melakukan proses panel regression"):
                try:
                    regression_results = run_panel_regression(
                        panel=config["panel"],
                        dependent_variables=config["dependent"],
                        independent_variables=config["independent"],
                    )

                    st.session_state["regression_results"] = (
                        regression_results
                    )
                    record_use("panel_regression")

                except Exception as exc:
                    st.error(f"Regression failed: {exc}")

        regression_results = st.session_state.get(
            "regression_results"
        )

        if regression_results is not None:
            st.subheader("Hasil panel regression")


            # Display numeric values without converting them
            # to strings, so users can sort and export them.
            st.dataframe(
                regression_results,
                use_container_width=True,
                hide_index=True,
            )

            csv_data = regression_results.to_csv(
                index=False
            ).encode("utf-8")