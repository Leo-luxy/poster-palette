#!/usr/bin/env python3
"""多策略聚类评测基准（Clustering Benchmark）
评估多类聚类算法（K-Means, Bisecting K-Means, GMM, Hierarchical Ward）
与多类特征空间（Base 5D, Contrast 6D, Spectral 15D）在 k in [3, 4, 5, 6] 下的表现。
输出度量指标包括几何分离度 (Silhouette, CH, DB)、簇均衡度及题材区分度 (Chi2, Cramér's V)。
"""
import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, BisectingKMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from scipy.stats import chi2_contingency

# 引入根目录公共模块
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from scripts import common

TARGET_GENRES = ['动画', '喜剧', '爱情', '剧情', '动作', '科幻', '犯罪', '恐怖']


def run_benchmark():
    print("=" * 70)
    print("开始多策略聚类基准测试 (Clustering Benchmark)...")
    print("=" * 70)

    # 1. 加载数据并做物理特征清洗
    df = common.load()
    feature_cols = ['mean_v', 'v_std', 'mean_s', 'colorful', 'hue']
    df = df.dropna(subset=feature_cols).copy()
    
    # 周期性色相展开 (0°=360° 拓扑连续)
    rad = np.deg2rad(df['hue'].values)
    df['sin_hue'] = np.sin(rad)
    df['cos_hue'] = np.cos(rad)

    # 2. 定义候选特征空间
    feature_spaces = {
        'Base_5D': ['mean_v', 'mean_s', 'colorful', 'sin_hue', 'cos_hue'],
        'Contrast_6D': ['mean_v', 'v_std', 'mean_s', 'colorful', 'sin_hue', 'cos_hue'],
        'Spectral_15D': ['mean_v', 'mean_s', 'colorful'] + [f'h{i}' for i in range(12)]
    }

    # 3. 候选算法模型构造器
    k_candidates = [3, 4, 5, 6]

    # 固定抽样子集用于快速高保真轮廓系数评估 (N=5000)
    sample_size = min(5000, len(df))
    sample_idx = np.random.RandomState(42).choice(len(df), size=sample_size, replace=False)

    records = []

    for feat_name, feat_cols in feature_spaces.items():
        print(f"\n[评估特征空间: {feat_name} (维数: {len(feat_cols)})]")
        X_raw = df[feat_cols].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)
        X_sub = X_scaled[sample_idx]

        for k in k_candidates:
            model_factories = {
                'K-Means': lambda: KMeans(n_clusters=k, random_state=42, n_init=10),
                'Bisecting-KMeans': lambda: BisectingKMeans(n_clusters=k, random_state=42),
                'GMM': lambda: GaussianMixture(n_components=k, random_state=42, n_init=3),
                'Hierarchical-Ward': lambda: AgglomerativeClustering(n_clusters=k, linkage='ward')
            }

            for model_name, factory in model_factories.items():
                t0 = time.time()
                model = factory()
                if model_name == 'GMM':
                    labels = model.fit(X_scaled).predict(X_scaled)
                else:
                    labels = model.fit_predict(X_scaled)
                cost_time = time.time() - t0

                # 几何分离度与紧凑度
                sil = silhouette_score(X_sub, labels[sample_idx])
                ch = calinski_harabasz_score(X_scaled, labels)
                db = davies_bouldin_score(X_scaled, labels)

                # 簇分布均衡度
                counts = pd.Series(labels).value_counts(normalize=True)
                min_pct = counts.min() * 100
                max_pct = counts.max() * 100

                # 真实电影题材区分度 (列联表卡方检验与 Cramér's V)
                df['tmp_cluster'] = labels
                ct_list = []
                for g in TARGET_GENRES:
                    sub = df[common.has_genre(df, g)]
                    c_counts = sub['tmp_cluster'].value_counts()
                    ct_list.append([c_counts.get(c, 0) for c in range(k)])
                ct_matrix = np.array(ct_list)
                chi2, p_val, dof, _ = chi2_contingency(ct_matrix)
                n_cells = ct_matrix.sum()
                min_dim = min(ct_matrix.shape) - 1
                cramers_v = np.sqrt(chi2 / (n_cells * min_dim)) if min_dim > 0 and n_cells > 0 else 0.0

                record = {
                    'FeatureSpace': feat_name,
                    'Model': model_name,
                    'k': k,
                    'Silhouette': round(sil, 4),
                    'Calinski_Harabasz': round(ch, 1),
                    'Davies_Bouldin': round(db, 3),
                    'MinClusterPct': round(min_pct, 1),
                    'MaxClusterPct': round(max_pct, 1),
                    'Chi2': round(chi2, 1),
                    'Cramers_V': round(cramers_v, 4),
                    'TimeSec': round(cost_time, 2)
                }
                records.append(record)
                print(f"  {model_name:18s} k={k} | Sil={sil:.4f} CH={ch:7.1f} DB={db:.3f} | "
                      f"Min%={min_pct:4.1f}% | Cramers_V={cramers_v:.4f} ({cost_time:4.2f}s)")

    benchmark_df = pd.DataFrame(records)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_csv = os.path.join(out_dir, 'clustering_benchmark.csv')
    benchmark_df.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"\n[完成] 基准评测结果已输出至: {out_csv}")

    # 排序与帕累托最优推荐
    # 最优筛选标准：Davies-Bouldin 尽量小，Cramér's V 尽量大，簇最小占比 >= 10%
    valid_candidates = benchmark_df[benchmark_df['MinClusterPct'] >= 10.0].copy()
    valid_candidates['RankScore'] = (
        valid_candidates['Silhouette'] * 2.0 +
        (1.0 / valid_candidates['Davies_Bouldin']) * 2.0 +
        valid_candidates['Cramers_V'] * 5.0
    )
    best_row = valid_candidates.sort_values(by='RankScore', ascending=False).iloc[0]

    print("\n" + "=" * 70)
    print("【综合最优策略选型评定】")
    print(f"最佳特征空间: {best_row['FeatureSpace']}")
    print(f"最佳算法模型: {best_row['Model']} (k={int(best_row['k'])})")
    print(f"评估指标: Silhouette={best_row['Silhouette']}, DB={best_row['Davies_Bouldin']} (最低/最佳), "
          f"CH={best_row['Calinski_Harabasz']}, Cramers_V={best_row['Cramers_V']} (题材区分峰值), "
          f"最小簇占比={best_row['MinClusterPct']}%")
    print("=" * 70)


if __name__ == '__main__':
    run_benchmark()
