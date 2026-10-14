import numpy as np
import pandas as pd
import streamlit as st

from scipy.stats import chi2
from linearmodels.panel import PanelOLS, RandomEffects


def hausman(fe_result, re_result):
    """Return the Hausman test p-value comparing FE and RE."""
    common = fe_result.params.index.intersection(
        re_result.params.index
    )

    if len(common) == 0:
        return np.nan

    b = fe_result.params.loc[common].to_numpy()
    B = re_result.params.loc[common].to_numpy()

    vb = fe_result.cov.loc[common, common].to_numpy()
    vB = re_result.cov.loc[common, common].to_numpy()

    diff = b - B
    cov_diff = vb - vB

    try:
        statistic = float(
            diff.T @ np.linalg.pinv(cov_diff) @ diff
        )

        if not np.isfinite(statistic) or statistic < 0:
            return np.nan

        return float(chi2.sf(statistic, df=len(common)))

    except (ValueError, np.linalg.LinAlgError):
        return np.nan


def run_panel_regression(
    panel,
    dependent_variables,
    independent_variables,
):
    """
    Run FE, RE, and Hausman tests for every dependent-independent
    variable combination.

    Expected columns:
        entity_id, year, and the selected variables.
    """
    if "year" not in panel.columns:
        raise ValueError(
            "Panel regression requires at least one selected "
            "time-varying variable with a detected year suffix."
        )

    results = []

    for dep in dependent_variables:
        for indep in independent_variables:

            result = {
                "DependentVar": dep,
                "IndependentVar": indep,
                "Observations": 0,
                "RECoef": np.nan,
                "REp-Value": np.nan,
                "FECoef": np.nan,
                "FEp-Value": np.nan,
                "Hausmanp-Value": np.nan,
                "Status": "OK",
            }

            try:
                # Use the source-row ID as the entity identifier.
                # This matches the existing build_panel() behavior.
                data = panel[
                    ["entity_id", "year", dep, indep]
                ].copy()

                data[dep] = pd.to_numeric(
                    data[dep], errors="coerce"
                )
                data[indep] = pd.to_numeric(
                    data[indep], errors="coerce"
                )

                data = data.replace(
                    [np.inf, -np.inf], np.nan
                ).dropna(
                    subset=["entity_id", "year", dep, indep]
                )

                data["year"] = pd.to_numeric(
                    data["year"], errors="raise"
                ).astype(int)

                data = data.set_index(
                    ["entity_id", "year"]
                ).sort_index()

                # Each entity-year combination must be unique.
                if data.index.has_duplicates:
                    raise ValueError(
                        "Duplicate entity-year observations."
                    )

                result["Observations"] = len(data)

                if data.empty:
                    raise ValueError("No usable observations.")

                if data.index.get_level_values(
                    "entity_id"
                ).nunique() < 2:
                    raise ValueError(
                        "At least two entities are required."
                    )

                if data.index.get_level_values(
                    "year"
                ).nunique() < 2:
                    raise ValueError(
                        "At least two years are required."
                    )

                # Add an intercept, as in your notebook.
                exog = data[[indep]].copy()
                exog.insert(0, "const", 1.0)

                # Fixed Effects
                fe_model = PanelOLS(
                    data[dep],
                    exog,
                    entity_effects=True,
                    drop_absorbed=True,
                )
                fe_result = fe_model.fit()

                # Random Effects
                re_model = RandomEffects(
                    data[dep],
                    exog,
                )
                re_result = re_model.fit()

                result["RECoef"] = re_result.params.get(
                    indep, np.nan
                )
                result["REp-Value"] = re_result.pvalues.get(
                    indep, np.nan
                )
                result["FECoef"] = fe_result.params.get(
                    indep, np.nan
                )
                result["FEp-Value"] = fe_result.pvalues.get(
                    indep, np.nan
                )

                if (
                    indep in fe_result.params.index
                    and indep in re_result.params.index
                ):
                    result["Hausmanp-Value"] = hausman(
                        fe_result, re_result
                    )
                else:
                    result["Status"] = (
                        "Hausman unavailable: coefficient "
                        "not estimable in both models."
                    )

            except Exception as exc:
                result["Status"] = str(exc)

            results.append(result)

    return pd.DataFrame(results)