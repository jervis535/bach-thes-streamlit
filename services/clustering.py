import pandas as pd
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import davies_bouldin_score
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import RobustScaler
from sklearn.decomposition import PCA

def remove_0(df):

    df=pd.read_csv(df)
    cols=[c for c in df.columns if c.split()[0] in ("luas","produksi","produktivitas")]

    all_zero=(df[cols].fillna(0)==0).all(axis=1)

    cleaned=df[~all_zero]
    return cleaned

def clustering_transformation(df):
    df=pd.read_csv("merged_era5_cleaned.csv")
    df_transformed=df.copy()

    log=['luas','produksi','produktivitas']
    robust=['humidity_avg','wind_avg','rainfall_mm','wind_max','temp_min','temp_max','temp_avg']
    standard=[]
    scalers={}

    def get_cols(g):
        return[c for c in df.columns if c.startswith(g+' ')]

    for g in log:
        cols = get_cols(g)

        data = df[cols].values
        data_log = np.log1p(data)

        df_transformed[cols] = data_log
        scalers[g] = ('log1p', None)


    for g in robust:
        cols=get_cols(g)

        data=df[cols].values

        scaler=RobustScaler()
        pooled=data.reshape(-1,1)
        scaler.fit(pooled)

        transformed=scaler.transform(pooled).reshape(data.shape)
        df_transformed[cols]=transformed
        scalers[g]=('robust',scaler)

    for g in standard:
        cols=get_cols(g)

        data=df[cols].values

        scaler=StandardScaler()
        pooled=data.reshape(-1,1)
        scaler.fit(pooled)

        transformed=scaler.transform(pooled).reshape(data.shape)
        df_transformed[cols]=transformed
        scalers[g]=('robust',scaler)

    df_transformed.to_csv("dataset_transformed.csv",index=False)
#------------------------------------------------------------

def clustering(df,kmin,kmax):
    df_transformed = pd.read_csv(df)

    exclude_cols = ['nama_kota','latitude','longitude','era5_latitude','era5_longitude','distance_km']
    feature_cols = [c for c in df_transformed.columns if c not in exclude_cols]

    var_groups = {}
    for c in feature_cols:
        var_name = re.sub(r'\s*\d{4}$', '', c)
        var_groups.setdefault(var_name, []).append(c)

    print(f"Variable groups ({len(var_groups)}): {list(var_groups.keys())}")

    pca_parts = []
    pca_models = {}
    summary = []

    for var_name, cols in var_groups.items():
        pca_var = PCA(n_components=0.90, svd_solver='full', random_state=42)
        scores = pca_var.fit_transform(df_transformed[cols].values)

        pca_models[var_name] = pca_var
        pca_parts.append(scores)
        summary.append({
            'variable': var_name,
            'n_original': len(cols),
            'n_components': pca_var.n_components_,
            'variance_explained': pca_var.explained_variance_ratio_.sum()
        })

    X_pca = np.hstack(pca_parts)
    pca_summary = pd.DataFrame(summary)
    print(pca_summary.to_string(index=False))
    print(f"\nOriginal features: {len(feature_cols)} -> PCA features: {X_pca.shape[1]}")
    print(f"Feature matrix shape: {X_pca.shape}")

    k_range = range(kmin,kmax)
    inertias=[]
    sil_scores=[]
    dbi_scores=[]


    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_pca)
        sil_scores.append(silhouette_score(X_pca,labels))
        dbi_scores.append(davies_bouldin_score(X_pca, labels))

    fig,axes=plt.subplots(1,2,figsize=(12,4))

    axes[0].plot(list(k_range),dbi_scores,marker='o',color='blue')
    axes[0].set_title('Davies-Bouldin Index')
    axes[0].set_xlabel('k')
    axes[0].set_ylabel('DBI')
    axes[0].grid(alpha=0.3)


    axes[1].plot(list(k_range), sil_scores, marker='o', color='orange')
    axes[1].set_title('Silhouette Score')
    axes[1].set_xlabel('k')
    axes[1].set_ylabel('Score')

    plt.tight_layout()
    plt.savefig("k_selection.png", dpi=100)
    plt.show()