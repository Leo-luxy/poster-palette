"""做法 B：无监督海报色型聚类基准评测、四类色型剖面、类型构成差值及年代分布。"""
import numpy as np
import pandas as pd
from sklearn.cluster import BisectingKMeans, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from b_common import (
    common,
    CLUSTER_IDS,
    CLUSTER_NAMES,
    HUE_COLS,
    MAIN_GENRES,
    SAT_FRAC_MIN,
    SEED,
    TABLES,
    describe_group,
    eligible_hue_mask,
    hue_summary_group,
    joint_movie_contrast,
    load_safe,
)

CONIC_FEATS = ["mean_v", "mean_s", "colorful", "scos_h", "ssin_h"]


def canonicalize_conic4(df_u: pd.DataFrame, raw_labels: np.ndarray) -> dict[int, int]:
    """根据物理不变量将 k=4 原始簇编号映射至固定语义顺序 0..3。"""
    tmp = df_u.assign(_raw=raw_labels)
    centers = tmp.groupby("_raw")[["mean_v", "scos_h"]].mean()
    bright_cl = int(centers["mean_v"].idxmax())
    dark_cl = int(centers["mean_v"].idxmin())
    rem = [c for c in range(4) if c not in (bright_cl, dark_cl)]
    warm_cl = max(rem, key=lambda c: float(centers.loc[c, "scos_h"]))
    cool_cl = min(rem, key=lambda c: float(centers.loc[c, "scos_h"]))
    return {bright_cl: 0, warm_cl: 1, cool_cl: 2, dark_cl: 3}


def subsample_ari(X: np.ndarray, full_labels: np.ndarray, model_kind: str, k: int, seed: int = SEED) -> float:
    """在 12 次 80% 随机无放回子样本上重训模型并计算与全量划分的平均 ARI 稳定性。"""
    rng = np.random.default_rng(seed)
    n = len(X)
    sub_n = int(0.80 * n)
    aris = []
    for b in range(12):
        idx = rng.choice(n, size=sub_n, replace=False)
        if model_kind == "K-Means":
            m = KMeans(n_clusters=k, random_state=100 + b, n_init=10).fit(X[idx])
            pred = m.predict(X)
        elif model_kind == "Bisecting-KMeans":
            m = BisectingKMeans(n_clusters=k, random_state=100 + b).fit(X[idx])
            pred = m.predict(X)
        else:
            m = GaussianMixture(n_components=k, random_state=100 + b, n_init=2).fit(X[idx])
            pred = m.predict(X)
        aris.append(adjusted_rand_score(full_labels, pred))
    return float(np.mean(aris))


def main() -> None:
    x = load_safe(verify_manifest=True)
    good = eligible_hue_mask(x, sat_min=SAT_FRAC_MIN)
    u = x.loc[good].copy().reset_index(drop=True)

    rad = np.deg2rad(u["hue"].to_numpy(dtype=float))
    u["cos_h"] = np.cos(rad)
    u["sin_h"] = np.sin(rad)
    u["scos_h"] = u["mean_s"].to_numpy(dtype=float) * u["cos_h"]
    u["ssin_h"] = u["mean_s"].to_numpy(dtype=float) * u["sin_h"]

    feature_spaces = {
        "Conic_5D": CONIC_FEATS,
        "Base_5D": ["mean_v", "mean_s", "colorful", "cos_h", "sin_h"],
        "Spectral_15D": ["mean_v", "mean_s", "colorful"] + HUE_COLS,
    }

    rng = np.random.default_rng(SEED)
    sil_idx = rng.choice(len(u), size=min(5000, len(u)), replace=False)

    # 1. 多特征空间 × 多算法 × k=2..6 统一口径基准评测 (N=19,072)
    bench_rows = []
    for space_name, cols in feature_spaces.items():
        X_sp = StandardScaler().fit_transform(u[cols].to_numpy(dtype=float))
        for k in [2, 3, 4, 5, 6]:
            for model_name in ["K-Means", "Bisecting-KMeans", "GMM"]:
                if model_name == "K-Means":
                    est = KMeans(n_clusters=k, random_state=SEED, n_init=20).fit(X_sp)
                    labels = est.labels_
                    inertia = float(est.inertia_)
                elif model_name == "Bisecting-KMeans":
                    est = BisectingKMeans(n_clusters=k, random_state=SEED).fit(X_sp)
                    labels = est.labels_
                    inertia = float(est.inertia_)
                else:
                    est = GaussianMixture(n_components=k, random_state=SEED, n_init=3).fit(X_sp)
                    labels = est.predict(X_sp)
                    inertia = np.nan

                sil = float(silhouette_score(X_sp[sil_idx], labels[sil_idx]))
                ch = float(calinski_harabasz_score(X_sp, labels))
                db = float(davies_bouldin_score(X_sp, labels))
                stab = subsample_ari(X_sp, labels, model_name, k, seed=SEED)
                vc = pd.Series(labels).value_counts(normalize=True) * 100.0

                bench_rows.append({
                    "n_movies": int(len(u)),
                    "feature_space": space_name,
                    "model": model_name,
                    "k": int(k),
                    "silhouette": round(sil, 4),
                    "calinski_harabasz": round(ch, 1),
                    "davies_bouldin": round(db, 4),
                    "stability_ari": round(stab, 4),
                    "min_cluster_pct": round(float(vc.min()), 2),
                    "max_cluster_pct": round(float(vc.max()), 2),
                    "inertia": round(inertia, 1) if np.isfinite(inertia) else np.nan,
                })
    pd.DataFrame(bench_rows).to_csv(TABLES / "cluster_benchmark.csv", index=False, encoding="utf-8")

    # 2. 主模型拟合：Conic_5D + K-Means (k=4) + PCA 二维投影
    scaler = StandardScaler()
    X_main = scaler.fit_transform(u[CONIC_FEATS].to_numpy(dtype=float))
    km_main = KMeans(n_clusters=4, random_state=SEED, n_init=20).fit(X_main)
    cmap = canonicalize_conic4(u, km_main.labels_)
    u["cluster"] = np.array([cmap[c] for c in km_main.labels_], dtype=int)
    u["cluster_name"] = u["cluster"].map(CLUSTER_NAMES)

    pca = PCA(n_components=2, random_state=SEED).fit(X_main)
    Z = pca.transform(X_main)
    # 固定主成分方向符号：令浓烈暖调(1)位于 PC1 正向，明亮浅调(0)位于 PC2 正向，保证跨平台完全一致
    if Z[u["cluster"] == 1, 0].mean() < 0:
        Z[:, 0] *= -1.0
        pca.components_[0, :] *= -1.0
    if Z[u["cluster"] == 0, 1].mean() < 0:
        Z[:, 1] *= -1.0
        pca.components_[1, :] *= -1.0

    u["pc1"] = Z[:, 0]
    u["pc2"] = Z[:, 1]

    u[["id", "year", "decade", "cluster", "cluster_name", "pc1", "pc2"]].to_csv(
        TABLES / "cluster_assignments.csv", index=False, encoding="utf-8"
    )
    pd.DataFrame(
        pca.components_,
        columns=CONIC_FEATS,
        index=[
            f"PC1 ({pca.explained_variance_ratio_[0]*100:.2f}%)",
            f"PC2 ({pca.explained_variance_ratio_[1]*100:.2f}%)",
        ],
    ).assign(explained_variance_ratio=pca.explained_variance_ratio_).to_csv(
        TABLES / "cluster_pca_loadings.csv", encoding="utf-8"
    )

    # 3. 四类客观色型汇总剖面表
    cluster_rows = []
    for cid in CLUSTER_IDS:
        sub = u[u["cluster"] == cid]
        desc = describe_group(sub, bootstrap_ci=True, seed=SEED)
        hue_d = hue_summary_group(sub, CLUSTER_NAMES[cid], sat_min=SAT_FRAC_MIN)
        r_ang = np.deg2rad(sub["hue"].to_numpy(dtype=float))
        msin, mcos = float(np.sin(r_ang).mean()), float(np.cos(r_ang).mean())
        circ_hue = float(np.rad2deg(np.arctan2(msin, mcos)) % 360.0)
        circ_r = float(np.hypot(msin, mcos))
        cluster_rows.append({
            "cluster": cid,
            "cluster_name": CLUSTER_NAMES[cid],
            "share": float(len(sub) / len(u)),
            "pc1_mean": float(sub["pc1"].mean()),
            "pc2_mean": float(sub["pc2"].mean()),
            "circular_hue_deg": circ_hue,
            "circular_resultant_r": circ_r,
            **desc,
            "warm_0_60": hue_d["warm_0_60"],
            "green_90_150": hue_d["green_90_150"],
            "cool_180_240": hue_d["cool_180_240"],
            **{f"h{i}": hue_d[f"h{i}"] for i in range(12)},
        })
    pd.DataFrame(cluster_rows).to_csv(TABLES / "cluster_summary.csv", index=False, encoding="utf-8")

    # 4. 9 大类型（及全库 ALL）在四类色型上的构成与联合 Bootstrap 差值 CI
    all_u_mask = np.ones(len(u), dtype=bool)
    base_shares = {cid: float((u["cluster"] == cid).mean()) for cid in CLUSTER_IDS}
    by_genre_rows = []
    for g in MAIN_GENRES + ["ALL"]:
        gm = all_u_mask if g == "ALL" else common.has_genre(u, g).to_numpy(dtype=bool)
        row_g: dict[str, str | int | float] = {"genre": g, "n_hue": int(gm.sum())}
        for cid in CLUSTER_IDS:
            ind = (u["cluster"].to_numpy() == cid).astype(float)
            row_g[f"share_c{cid}"] = float(ind[gm].mean())
            if g == "ALL":
                row_g[f"diff_c{cid}"] = 0.0
                row_g[f"diff_c{cid}_ci_low"] = 0.0
                row_g[f"diff_c{cid}_ci_high"] = 0.0
            else:
                ct = joint_movie_contrast(ind, gm, all_u_mask, seed=SEED)
                row_g[f"diff_c{cid}"] = ct["mean_difference"]
                row_g[f"diff_c{cid}_ci_low"] = ct["ci_low"]
                row_g[f"diff_c{cid}_ci_high"] = ct["ci_high"]
        by_genre_rows.append(row_g)
    pd.DataFrame(by_genre_rows).to_csv(TABLES / "cluster_by_genre.csv", index=False, encoding="utf-8")

    # 5. 1950s—2020s 各年代在四类色型上的构成占比
    by_decade_rows = []
    for dec, grp in u.groupby("decade", sort=True):
        vc = grp["cluster"].value_counts(normalize=True).reindex(CLUSTER_IDS, fill_value=0.0)
        by_decade_rows.append({
            "decade": int(dec),
            "n_hue": int(len(grp)),
            **{f"share_c{cid}": float(vc[cid]) for cid in CLUSTER_IDS},
        })
    pd.DataFrame(by_decade_rows).to_csv(TABLES / "cluster_by_decade.csv", index=False, encoding="utf-8")

    # 6. 聚类 sat_frac 敏感性核验（不过滤近灰全部 N=19,694 vs 不同 sat_frac 阈值）
    sat_sens_rows = []
    x_full = x.copy()
    h_num = pd.to_numeric(x_full["hue"], errors="coerce").to_numpy(dtype=float)
    has_h = np.isfinite(h_num)
    rad_full = np.deg2rad(np.where(has_h, h_num, 0.0))
    x_full["scos_h"] = np.where(has_h, x_full["mean_s"].to_numpy(dtype=float) * np.cos(rad_full), 0.0)
    x_full["ssin_h"] = np.where(has_h, x_full["mean_s"].to_numpy(dtype=float) * np.sin(rad_full), 0.0)

    for th in [0.0, 0.05, 0.10, 0.15, 0.20]:
        mk = np.ones(len(x_full), dtype=bool) if th == 0.0 else eligible_hue_mask(x_full, sat_min=th)
        sub_t = x_full.loc[mk].copy().reset_index(drop=True)
        Xt = StandardScaler().fit_transform(sub_t[CONIC_FEATS].to_numpy(dtype=float))
        kmt = KMeans(n_clusters=4, random_state=SEED, n_init=20).fit(Xt)
        mp_t = canonicalize_conic4(sub_t, kmt.labels_)
        cl_t = np.array([mp_t[c] for c in kmt.labels_], dtype=int)
        sub_t["cl_t"] = cl_t
        merged_overlap = u[["id", "cluster"]].merge(sub_t[["id", "cl_t"]], on="id", how="inner")
        ari_vs_main = float(adjusted_rand_score(merged_overlap["cluster"], merged_overlap["cl_t"]))
        vc_t = pd.Series(cl_t).value_counts(normalize=True).reindex(CLUSTER_IDS, fill_value=0.0)
        sat_sens_rows.append({
            "sat_frac_threshold": th,
            "n_movies": int(len(sub_t)),
            "n_common_with_main": int(len(merged_overlap)),
            "ari_vs_main_010": round(ari_vs_main, 4),
            **{f"share_c{cid}": round(float(vc_t[cid]), 4) for cid in CLUSTER_IDS},
        })
    pd.DataFrame(sat_sens_rows).to_csv(TABLES / "cluster_sat_sensitivity.csv", index=False, encoding="utf-8")

    print(
        f"做法 B 完成：N={len(u):,} 部聚类（4 类占比 "
        + ", ".join(f"{CLUSTER_NAMES[c]} {base_shares[c]*100:.1f}%" for c in CLUSTER_IDS)
        + f"），PCA 前两轴解释方差 {pca.explained_variance_ratio_.sum()*100:.1f}%。"
    )


if __name__ == "__main__":
    main()
