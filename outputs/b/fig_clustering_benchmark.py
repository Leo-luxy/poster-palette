#!/usr/bin/env python3
"""多策略聚类评测与模型选型诊断图（Clustering Benchmark Dashboard）
读取 outputs/b/clustering_benchmark.csv 中的 48 组策略实验结果，
渲染 4 面板高保真模型选型诊断大图：
- 面板 A：簇数 k 选型与 Davies-Bouldin 肘部极小值曲线
- 面板 B：几何轮廓系数 vs 题材关联度 (Cramér's V) 帕累托前沿散点图
- 面板 C：3 大特征表征空间下的分离度退化剖析 (CH 指标与 DB 指标)
- 面板 D：最终选定的 4 大物理色型质心特征雷达图 (Radar Profile)

输出：
- figures/fig_clustering_benchmark.png （300 DPI 高清大图）
"""
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# 引入项目 common 模块
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from scripts import common

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def render_benchmark_dashboard():
    print(">>> [1/3] 载入 48 组策略评测数据...")
    csv_path = os.path.join(ROOT, 'outputs', 'b', 'clustering_benchmark.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"未找到基准数据表: {csv_path}，请先执行 clustering_benchmark.py")
    
    bench_df = pd.read_csv(csv_path)

    print(">>> [2/3] 计算最优 4 大色型的物理质心雷达特征...")
    df = common.load()
    feature_cols = ['mean_v', 'mean_s', 'colorful', 'hue']
    df_u = df.dropna(subset=feature_cols).copy()
    rad = np.deg2rad(df_u['hue'].values)
    df_u['sin_hue'] = np.sin(rad)
    df_u['cos_hue'] = np.cos(rad)

    feats = ['mean_v', 'mean_s', 'colorful', 'sin_hue', 'cos_hue']
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_u[feats].values)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    raw_labels = kmeans.fit_predict(X_scaled)
    
    # 物理不变量锁定：确保无论 KMeans 初始标签顺序如何，0/1/2/3 严格绑定其物理色型
    centers_unscaled = scaler.inverse_transform(kmeans.cluster_centers_)
    hues = [np.rad2deg(np.arctan2(centers_unscaled[c, 3], centers_unscaled[c, 4])) % 360 for c in range(4)]
    mean_vs = [centers_unscaled[c, 0] for c in range(4)]
    colorfulness = [centers_unscaled[c, 2] for c in range(4)]
    
    blue_idx = int(np.argmin([abs(h - 225) for h in hues]))
    remaining = [c for c in range(4) if c != blue_idx]
    colorful_idx = max(remaining, key=lambda c: colorfulness[c])
    remaining = [c for c in remaining if c != colorful_idx]
    dark_idx = min(remaining, key=lambda c: mean_vs[c])
    bright_idx = max(remaining, key=lambda c: mean_vs[c])
    
    canonical_map = {
        blue_idx: 0,     # 冷光青蓝调
        dark_idx: 1,     # 极致暗黑调
        colorful_idx: 2, # 高饱和艳丽调
        bright_idx: 3    # 高亮通透调
    }
    df_u['cluster'] = np.array([canonical_map[l] for l in raw_labels])

    # 4 大色型名称与代表色 (含全库精确样本量与占比)
    c_counts = df_u['cluster'].value_counts()
    c_pcts = df_u['cluster'].value_counts(normalize=True) * 100
    cluster_meta = {
        0: {'name': f"冷光青蓝调 (n={c_counts[0]:,}, {c_pcts[0]:.1f}%)", 'color': '#2b6cb0'},
        1: {'name': f"极致暗黑调 (n={c_counts[1]:,}, {c_pcts[1]:.1f}%)", 'color': '#2d3748'},
        2: {'name': f"高饱和艳丽调 (n={c_counts[2]:,}, {c_pcts[2]:.1f}%)", 'color': '#d69e2e'},
        3: {'name': f"高亮通透调 (n={c_counts[3]:,}, {c_pcts[3]:.1f}%)", 'color': '#e53e3e'}
    }

    # 提取雷达指标均值（0-1 极差归一化方便在同一雷达图上对比）
    radar_metrics = ['mean_v', 'mean_s', 'colorful', 'h7', 'h0'] # 明度、饱和度、丰富度、蓝光扇区h7、暖红扇区h0
    radar_labels = ['平均明度\n(mean_v)', '平均饱和度\n(mean_s)', '色彩丰富度\n(colorful)', '青蓝波段占比\n(210-240°)', '暖红波段占比\n(0-30°)']
    
    radar_data = {}
    for c_id in range(4):
        c_sub = df_u[df_u['cluster'] == c_id]
        vals = []
        for m in radar_metrics:
            # 采用全库 min-max 归一化
            v_min = df_u[m].quantile(0.01)
            v_max = df_u[m].quantile(0.99)
            norm_val = np.clip((c_sub[m].mean() - v_min) / (v_max - v_min), 0.05, 0.95)
            vals.append(norm_val)
        radar_data[c_id] = vals

    print(">>> [3/3] 渲染 4 面板高保真模型选型诊断图 (300 DPI)...")
    fig = plt.figure(figsize=(16.8, 11.2))
    gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.22)

    # -------------------------------------------------------------
    # 面板 A：簇数 k 选型与 Davies-Bouldin 曲线 (越低越好)
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0, 0])
    base_df = bench_df[bench_df['FeatureSpace'] == 'Base_5D']
    
    model_styles = {
        'K-Means': {'color': '#c53030', 'marker': 'o', 'lw': 2.4},
        'Bisecting-KMeans': {'color': '#3182ce', 'marker': 's', 'lw': 1.8},
        'Hierarchical-Ward': {'color': '#805ad5', 'marker': '^', 'lw': 1.8},
        'GMM': {'color': '#718096', 'marker': 'x', 'lw': 1.5, 'ls': '--'}
    }

    for m_name, style in model_styles.items():
        sub = base_df[base_df['Model'] == m_name].sort_values('k')
        ax_a.plot(sub['k'], sub['Davies_Bouldin'], label=m_name,
                  color=style['color'], marker=style['marker'], lw=style['lw'],
                  ls=style.get('ls', '-'), markersize=7)

    # 标注最低极值点 (K-Means, k=4, DB=1.211)
    ax_a.scatter([4], [1.211], s=160, facecolors='none', edgecolors='#c53030', lw=2.5, zorder=5)
    ax_a.annotate('全局最优极小值\nK-Means (k=4, DB=1.211)', xy=(4, 1.211), xytext=(4.15, 1.60),
                  arrowprops=dict(arrowstyle="->", color='#c53030', lw=1.8),
                  fontsize=9, fontweight='bold', color='#9b2c2c',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fff5f5', ec='#e53e3e', alpha=0.95))

    # 标注 GMM 越界失效说明（解释虚线截断成因）
    ax_a.annotate('GMM 失效出界\n(k=5 时 DB=7.78)', xy=(4.18, 4.28), xytext=(4.35, 3.82),
                  arrowprops=dict(arrowstyle="->", color='#718096', lw=1.2),
                  fontsize=7.8, color='#4a5568',
                  bbox=dict(boxstyle="round,pad=0.2", fc='#f7fafc', ec='#cbd5e0', alpha=0.92))

    ax_a.set_xticks([3, 4, 5, 6])
    ax_a.set_xlabel('聚类簇数 (k)', fontsize=10.5, fontweight='bold')
    ax_a.set_ylabel('Davies-Bouldin 指标 (越小分离度越优)', fontsize=10.5, fontweight='bold')
    ax_a.set_ylim(0.9, 4.3)
    ax_a.grid(alpha=0.3, linestyle=':')
    ax_a.legend(loc='upper right', fontsize=9, framealpha=0.95)
    ax_a.set_title('面板 A：簇数 k 选型与聚类分离度曲线 (Base_5D 特征空间)',
                   fontsize=11.5, fontweight='bold', pad=10)

    # -------------------------------------------------------------
    # 面板 B：几何轮廓系数 vs 题材关联度 (Cramér's V) 帕累托前沿
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[0, 1])
    
    # 散点图展示所有 48 个策略
    palette_map = {
        'Base_5D': '#2b6cb0',
        'Contrast_6D': '#dd6b20',
        'Spectral_15D': '#718096'
    }

    for feat_name, col in palette_map.items():
        sub = bench_df[bench_df['FeatureSpace'] == feat_name]
        # 实心点表示均衡簇(Min% >= 10%), 空心点表示发生退化坍缩(Min% < 10%)
        valid = sub[sub['MinClusterPct'] >= 10.0]
        invalid = sub[sub['MinClusterPct'] < 10.0]
        
        ax_b.scatter(valid['Silhouette'], valid['Cramers_V'],
                     color=col, s=65, alpha=0.85, label=f"{feat_name} (均衡)", edgecolors='white', lw=0.6)
        if len(invalid) > 0:
            ax_b.scatter(invalid['Silhouette'], invalid['Cramers_V'],
                         facecolors='none', edgecolors=col, s=45, alpha=0.6,
                         linestyle='--', label=f"{feat_name} (退化坍缩)")

    # 绘制帕累托最优前沿线 (Pareto Efficient Frontier)
    pareto_pts = [
        (0.2656, 0.1217), # Base_5D k=3
        (0.2629, 0.1581), # Base_5D k=5
        (0.2573, 0.1607), # Base_5D k=4 (Knee Point / 全局最优)
        (0.2101, 0.1617)  # Contrast_6D k=5
    ]
    px, py = zip(*pareto_pts)
    ax_b.plot(px, py, color='#c53030', ls=':', lw=1.8, alpha=0.85, label='帕累托前沿 (Pareto Frontier)', zorder=4)

    # 高亮最优选型拐点 (Base_5D, K-Means, k=4)
    best_sil = 0.2573
    best_cv = 0.1607
    ax_b.scatter([best_sil], [best_cv], s=200, facecolors='#e53e3e', edgecolors='#742a2a', lw=2.2, zorder=6)
    ax_b.annotate('帕累托拐点最优解 (Knee Point)\nBase_5D + K-Means (k=4)\n(Sil=0.257, V=0.161, DB=1.211 最优)',
                  xy=(best_sil, best_cv), xytext=(best_sil - 0.13, best_cv + 0.016),
                  arrowprops=dict(arrowstyle="->", color='#c53030', lw=1.8),
                  fontsize=8.5, fontweight='bold', color='#742a2a',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fff5f5', ec='#e53e3e', alpha=0.95),
                  zorder=7)

    ax_b.set_xlabel('轮廓系数 Silhouette (几何紧致分离度)', fontsize=10.5, fontweight='bold')
    ax_b.set_ylabel('题材关联度 Cramér\'s V (与8大题材的自然区分度)', fontsize=10.5, fontweight='bold')
    ax_b.set_xlim(-0.05, 0.30)
    ax_b.set_ylim(0.05, 0.20)
    ax_b.grid(alpha=0.3, linestyle=':')
    ax_b.legend(loc='lower left', fontsize=8.5, framealpha=0.92)
    ax_b.set_title('面板 B：几何聚类紧致度 vs 题材外部效度 (帕累托权衡)',
                   fontsize=11.5, fontweight='bold', pad=10)

    # -------------------------------------------------------------
    # 面板 C：3 大特征表征空间在 K-Means (k=4) 下的分离度对比
    # -------------------------------------------------------------
    ax_c = fig.add_subplot(gs[1, 0])
    comp_feats = ['Base_5D', 'Contrast_6D', 'Spectral_15D']
    comp_rows = bench_df[(bench_df['Model'] == 'K-Means') & (bench_df['k'] == 4)]
    comp_rows = comp_rows.set_index('FeatureSpace').reindex(comp_feats)

    pos = np.arange(len(comp_feats))
    bwidth = 0.35

    ax_c_twin = ax_c.twinx()
    
    # 左轴：Calinski-Harabasz (柱状图)
    bars_ch = ax_c.bar(pos - bwidth/2, comp_rows['Calinski_Harabasz'], bwidth,
                       color='#3182ce', alpha=0.88, label='Calinski-Harabasz 指标 (左轴, 越高越优)')
    for idx, v in enumerate(comp_rows['Calinski_Harabasz']):
        ax_c.text(idx - bwidth/2, v + 120, f"{v:.1f}", ha='center', fontsize=8.5, fontweight='bold', color='#1a365d')

    # 右轴：Davies-Bouldin (柱状图)
    bars_db = ax_c_twin.bar(pos + bwidth/2, comp_rows['Davies_Bouldin'], bwidth,
                            color='#dd6b20', alpha=0.88, label='Davies-Bouldin 指标 (右轴, 越低越优)')
    for idx, v in enumerate(comp_rows['Davies_Bouldin']):
        ax_c_twin.text(idx + bwidth/2, v + 0.05, f"{v:.3f}", ha='center', fontsize=8.5, fontweight='bold', color='#7b341e')

    ax_c.set_xticks(pos)
    feat_labels = ['Base_5D\n(5维宏观+正余弦)', 'Contrast_6D\n(加入明暗标准差)', 'Spectral_15D\n(12扇区高维直方图)']
    ax_c.set_xticklabels(feat_labels, fontsize=9.5, fontweight='bold')
    ax_c.set_ylabel('Calinski-Harabasz 指标', fontsize=10.5, fontweight='bold', color='#2b6cb0')
    ax_c_twin.set_ylabel('Davies-Bouldin 指标', fontsize=10.5, fontweight='bold', color='#dd6b20')
    ax_c.set_ylim(0, 8400)
    ax_c_twin.set_ylim(0.5, 2.4)
    ax_c.grid(axis='y', alpha=0.25, linestyle=':')

    # 标注维数灾难与共线性失效说明
    fail_box = ("特征空间退化机理：\n"
                "• Spectral_15D: 稀疏直方图维数灾难\n"
                "  CH腰斩 (6947→2201), 最小簇跌至 8.0%\n"
                "• Contrast_6D: 明暗差与均值强约束\n"
                "  引入非线性冗余噪声")
    ax_c.text(0.03, 0.96, fail_box, transform=ax_c.transAxes,
              verticalalignment='top', fontsize=8.0,
              bbox=dict(boxstyle="round,pad=0.35", fc='#f7fafc', ec='#cbd5e0', alpha=0.95))

    # 合并图例
    ax_c.legend([bars_ch, bars_db], [bars_ch.get_label(), bars_db.get_label()],
                loc='upper right', fontsize=8.2, framealpha=0.92)
    ax_c.set_title('面板 C：特征空间维度对比 (K-Means k=4 呈现维数灾难与共线性退化)',
                   fontsize=11.5, fontweight='bold', pad=10)

    # -------------------------------------------------------------
    # 面板 D：最终选定的 4 大物理色型质心特征雷达图
    # -------------------------------------------------------------
    ax_d = fig.add_subplot(gs[1, 1], projection='polar')
    
    num_vars = len(radar_labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1] # 闭合多边形

    for c_id, meta in cluster_meta.items():
        vals = radar_data[c_id]
        vals_loop = vals + vals[:1]
        ax_d.plot(angles, vals_loop, color=meta['color'], lw=2.2, label=meta['name'])
        ax_d.fill(angles, vals_loop, color=meta['color'], alpha=0.15)

    ax_d.set_theta_offset(np.pi / 2)
    ax_d.set_theta_direction(-1)
    ax_d.set_xticks(angles[:-1])
    ax_d.set_xticklabels(radar_labels, fontsize=8.5, fontweight='bold')
    ax_d.set_ylim(0, 1.0)
    ax_d.set_rgrids([0.25, 0.50, 0.75], labels=['25%', '50%', '75%'], fontsize=7.5, color='#718096')
    ax_d.grid(alpha=0.35, linestyle=':')
    ax_d.legend(loc='upper right', bbox_to_anchor=(1.25, 1.05), fontsize=8.5, framealpha=0.92)
    ax_d.set_title('面板 D：最优 4 大物理色型多维质心特征雷达图 (0~100% 分位数归一化)',
                   fontsize=11.0, fontweight='bold', pad=14)

    plt.suptitle('多策略聚类评测基准与最优模型选型证据链 (Clustering Benchmark & Model Selection)',
                 fontsize=14.0, fontweight='bold', y=0.98)
    fig.subplots_adjust(top=0.91, bottom=0.08, left=0.06, right=0.95)

    out_fig = os.path.join(common.FIG, 'fig_clustering_benchmark.png')
    plt.savefig(out_fig, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"    模型选型诊断大图已保存至: {out_fig}")
    return out_fig


if __name__ == '__main__':
    render_benchmark_dashboard()
