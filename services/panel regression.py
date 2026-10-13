from scipy.stats import chi2
import numpy as np
from linearmodels.panel import PanelOLS, RandomEffects
import pandas as pd

def hausman(fe, re):
    b=fe.params
    B=re.params

    common=b.index.intersection(B.index)

    b=b[common]
    B=B[common]

    vb=fe.cov.loc[common,common]
    vB=re.cov.loc[common,common]

    diff=b-B
    covdiff=vb-vB

    try:
        stat=np.dot(np.dot(diff.T,np.linalg.inv(covdiff)),diff)
        pvalue=1-chi2.cdf(stat,len(diff))
    except:
        pvalue=np.nan

    return pvalue

def panel_regression(df):
    df=pd.read_csv(df)

    years=list(range(2010, 2025))
    records=[]

    for _, row in df.iterrows():
        for yr in years:
            records.append({

                "Region":row["nama_kota"],
                "Year":yr,

                "Production":row[f"produksi {yr}"],
                "LandArea":row[f"luas {yr}"],
                "Productivity":row[f"produktivitas {yr}"],

                "MinimumTemperature":row[f"temp_min {yr}"],
                "AverageTemperature":row[f"temp_avg {yr}"],
                "MaximumTemperature":row[f"temp_max {yr}"],

                "Humidity":row[f"humidity_avg {yr}"],
                "Rainfall":row[f"rainfall_mm {yr}"],

                "AverageWind":row[f"wind_max {yr}"],
                "MaximumWind":row[f"wind_avg {yr}"]

            })

    panel=pd.DataFrame(records)
    panel=panel.dropna()
    panel=panel.set_index(["Region","Year"])

    independent_variables=[
        "MinimumTemperature",
        "MaximumTemperature",
        "AverageTemperature",
        "Humidity",
        "Rainfall",
        "MaximumWind",
        "AverageWind"
    ]

    dependent_variables=[
        "Production",
        "LandArea",
        "Productivity"
    ]

    results = []

    for indep in independent_variables:
        for dep in dependent_variables:
            data=panel[[dep,indep]].dropna()

            fe_model=PanelOLS.from_formula(
                f"{dep}~1+{indep}+EntityEffects",
                data=data
            )
            fe_result=fe_model.fit()

            re_model=RandomEffects.from_formula(
                f"{dep}~1+{indep}",
                data=data
            )
            re_result=re_model.fit()

            hausman_p=hausman(fe_result,re_result)
            results.append({

                "IndependentVar":indep,
                "DependentVar":dep,

                "RECoef":re_result.params[indep],
                "REp-Value":re_result.pvalues[indep],

                "FECoef":fe_result.params[indep],
                "FEp-Value":fe_result.pvalues[indep],

                "Hausmanp-Value":hausman_p

            })

    result_table = pd.DataFrame(results)

    for col in ["RECoef","REp-Value","FECoef","FEp-Value","Hausmanp-Value"]:
        result_table[col]=result_table[col].apply(lambda x:f"{x:.6g}")
    return (result_table)
    #result_table.to_excel("results/panel_regression.xlsx",index=False)


