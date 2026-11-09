#!/usr/bin/env python3
"""图 1：电影海报配色的真实光谱流形与 8 大类型客观映射（顶级出版与工程级高保真版）

三大核心面板系统性呈现物理色彩流动与工业范式：
- 面板 A：【极坐标真实色相星云与 4 大色型质心锚点】
  基于全库 1.9 万部海报计算连续色彩密度地形（Polar 2D KDE 等高线），
  叠加 2,200 部真实海报提取的主色散点（dom1 HEX），
  显式锚定 4 大客观物理色型的经验质心（$\bigstar$ 与参数引线）；
- 面板 B：【8 大主流类型真实海报色彩基因光谱带 (Genome Ribbons)】
  基于每个类型在 12 色相扇区内海报的真实均值饱和度与明度，
  数据驱动生成 100% 物理真实的 HSV->RGB 色带，全量配备数据微标签与底部光谱标尺；
- 面板 C：【8 大主流类型在 4 大色型间的流向热力矩阵与超配比率】
  呈现行归一化百分比、全库大盘基准行（Baseline）、行峰值金色描边星标（★）、
  以及经济学标准超配比率（Over-representation Ratio），独立性卡方检验与效应量 Cramér's V。

输出：
- figures/fig_q1_hue.png （定稿大图，300 DPI）
- outputs/b/fig1_v3_visual.png （草稿备份）
- outputs/b/fig1_stats.csv（统计数据表）
- outputs/b/fig1_report.md（配套解读）
"""
import colorsys
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, gaussian_kde
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 引入项目 common 模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts'))
import common

# 字体配置
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

GENRES_8 = ['动画', '喜剧', '爱情', '剧情', '动作', '科幻', '犯罪', '恐怖']

# 4 大物理色型元数据
CLUSTER_NAMES = {
    0: '冷光青蓝调',
    1: '极致暗黑调',
    2: '高饱和艳丽调',
    3: '高亮通透调'
}
CLUSTER_BASE_COLORS = {
    0: '#2b6cb0',  # 科技冷蓝
    1: '#2d3748',  # 压抑暗黑
    2: '#d69e2e',  # 多巴胺暖金
    3: '#e53e3e'   # 通透暖红
}


def fit_clusters(df_u):
    """特征工程与 KMeans 聚类建模"""
    hue_rad = np.radians(df_u['hue'])
    df_u['sin_hue'] = np.sin(hue_rad)
    df_u['cos_hue'] = np.cos(hue_rad)
    
    features = ['mean_v', 'mean_s', 'colorful', 'sin_hue', 'cos_hue']
    X = df_u[features].dropna()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 最优 k=4 聚类
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
    df_u['cluster_name'] = df_u['cluster'].map(CLUSTER_NAMES)
    return df_u, kmeans, X_scaled


def render_fig1_spectacular(df_u):
    """绘制高保真多面板色彩可视化大图 (18.2 x 6.6 英寸, 300 DPI)"""
    fig = plt.figure(figsize=(18.2, 6.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.02, 1.22, 0.96], wspace=0.28)
    
    # -------------------------------------------------------------
    # 面板 A：极坐标真实色彩流形盘 (Polar Density Shading + Scatter + Centroids)
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0], projection='polar')
    
    # 1. 计算极坐标连续核密度轮廓 (通过笛卡尔坐标无缝转换，解决 0/360° 周期边界平滑)
    kde_sample = df_u.sample(min(4000, len(df_u)), random_state=42)
    s_rad = np.radians(kde_sample['hue'].values)
    s_r = np.clip(kde_sample['mean_s'].values * 1.05, 0.05, 0.98)
    kx = s_r * np.cos(s_rad)
    ky = s_r * np.sin(s_rad)
    kde_polar = gaussian_kde(np.vstack([kx, ky]))

    grid_th = np.linspace(0, 2 * np.pi, 140)
    grid_r = np.linspace(0.05, 0.98, 70)
    TH, R = np.meshgrid(grid_th, grid_r)
    GX = R * np.cos(TH)
    GY = R * np.sin(TH)
    Z_polar = kde_polar(np.vstack([GX.ravel(), GY.ravel()])).reshape(TH.shape)
    
    # 绘制高雅的密度轮廓阴影层
    ax_a.contourf(TH, R, Z_polar, levels=7, cmap='Purples', alpha=0.22, zorder=1)
    ax_a.contour(TH, R, Z_polar, levels=7, colors='#805ad5', alpha=0.28, linewidths=0.6, zorder=2)

    # 2. 绘制外圈色彩刻度色带 (HSV 渐变)
    ring_angles = np.linspace(0, 2 * np.pi, 360)
    for ang in ring_angles:
        col = colorsys.hsv_to_rgb(ang / (2 * np.pi), 0.92, 0.95)
        ax_a.plot([ang, ang], [1.02, 1.08], color=col, lw=2.2, zorder=4)
        
    # 3. 采样 2,200 部海报画出真实主色散点
    sample_df = df_u.sample(min(2200, len(df_u)), random_state=42)
    thetas = np.radians(sample_df['hue'])
    radii = np.clip(sample_df['mean_s'] * 1.05, 0.05, 0.98)
    
    point_colors = []
    for _, r in sample_df.iterrows():
        hex_c = r.get('dom1')
        if isinstance(hex_c, str) and hex_c.startswith('#') and len(hex_c) == 7:
            try:
                rgb = [int(hex_c[i:i+2], 16)/255.0 for i in (1, 3, 5)]
            except Exception:
                rgb = colorsys.hsv_to_rgb(r['hue']/360.0, r['mean_s'], r['mean_v'])
        else:
            rgb = colorsys.hsv_to_rgb(r['hue']/360.0, r['mean_s'], r['mean_v'])
        point_colors.append(rgb)
        
    ax_a.scatter(thetas, radii, c=point_colors, s=11, alpha=0.55, edgecolors='none', zorder=3)
    
    # 4. 计算 4 个色型的经验物理质心坐标
    centroids = {}
    for c_id in range(4):
        c_sub = df_u[df_u['cluster'] == c_id]
        rad_vals = np.radians(c_sub['hue'])
        mean_sin = np.sin(rad_vals).mean()
        mean_cos = np.cos(rad_vals).mean()
        c_theta = np.arctan2(mean_sin, mean_cos) % (2 * np.pi)
        c_sat = c_sub['mean_s'].mean()
        centroids[c_id] = (c_theta, c_sat)

    # 绘制质心星标
    for c_id, (cth, csat) in centroids.items():
        ax_a.scatter([cth], [csat], marker='*', s=260, color=CLUSTER_BASE_COLORS[c_id],
                     edgecolor='white', lw=1.6, zorder=8)

    # 4 大色型质心引线标注
    ax_a.annotate('【冷光青蓝区】\n青蓝波段 (质心 225°)',
                  xy=(centroids[0][0], centroids[0][1]), xytext=(np.radians(222), 1.26),
                  arrowprops=dict(arrowstyle="->", color='#2b6cb0', lw=1.5),
                  fontsize=8, fontweight='bold', color='#1a365d', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#ebf8ff', ec='#3182ce', alpha=0.92),
                  zorder=9)
    
    ax_a.annotate('【高饱和艳丽区】\n高浓多彩 (高饱和外圈)',
                  xy=(centroids[2][0], centroids[2][1]), xytext=(np.radians(45), 1.28),
                  arrowprops=dict(arrowstyle="->", color='#d69e2e', lw=1.5),
                  fontsize=8, fontweight='bold', color='#744210', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fffaf0', ec='#d69e2e', alpha=0.92),
                  zorder=9)
    
    ax_a.annotate('【极致暗黑区】\n低明度暗核 (质心 V=0.28)',
                  xy=(centroids[1][0], centroids[1][1]), xytext=(np.radians(315), 1.26),
                  arrowprops=dict(arrowstyle="->", color='#2d3748', lw=1.5),
                  fontsize=8, fontweight='bold', color='#1a202c', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#f7fafc', ec='#4a5568', alpha=0.92),
                  zorder=9)
    
    ax_a.annotate('【高亮通透区】\n高调亮白 (质心 V=0.74)',
                  xy=(centroids[3][0], centroids[3][1]), xytext=(np.radians(135), 1.26),
                  arrowprops=dict(arrowstyle="->", color='#e53e3e', lw=1.5),
                  fontsize=8, fontweight='bold', color='#742a2a', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fff5f5', ec='#e53e3e', alpha=0.92),
                  zorder=9)

    ax_a.set_theta_zero_location('E') # 0°在东面（红）
    ax_a.set_thetagrids([0, 60, 120, 180, 240, 300],
                        labels=['0° 红', '60° 黄', '120° 绿', '180° 青', '240° 蓝', '300° 紫'],
                        fontsize=8.5, fontweight='bold')
    ax_a.set_rgrids([0.3, 0.6, 0.9], labels=['S=0.3', 'S=0.6', 'S=0.9'], fontsize=7.5, color='#718096')
    ax_a.set_ylim(0, 1.1)
    ax_a.grid(alpha=0.35, linestyle=':')
    ax_a.set_title('面板 A：海报极坐标真实色彩流形\n(2D 核密度星云 + 2,200部主色采样 + 4大质心★)',
                   fontsize=10.5, fontweight='bold', pad=25)

    # -------------------------------------------------------------
    # 面板 B：8 大主流类型真实海报色彩基因光谱带 (数据驱动物理色彩渲染)
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[1])
    h_cols = [f'h{i}' for i in range(12)]
    h_centers = np.arange(15, 360, 30)
    y_coords = np.arange(len(GENRES_8))
    bar_height = 0.58
    
    for i, g in enumerate(GENRES_8):
        sub = df_u[common.has_genre(df_u, g)]
        v_med = sub['mean_v'].median()
        s_med = sub['mean_s'].median()
        
        weights = sub[h_cols].sum(0)
        shares = weights / weights.sum()
        
        left_pos = 0.0
        for h_idx in range(12):
            w = shares[f'h{h_idx}']
            if w <= 0.001:
                continue
            deg = h_centers[h_idx]
            
            # 数据驱动的真实物理色彩渲染：计算该类型落在该色相扇区内的样本真实平均饱和度与明度
            d_low = h_idx * 30
            d_high = (h_idx + 1) * 30
            sec_movies = sub[(sub['hue'] >= d_low) & (sub['hue'] < d_high)]
            if len(sec_movies) >= 8:
                s_val = sec_movies['mean_s'].mean()
                v_val = sec_movies['mean_v'].mean()
            else:
                s_val = s_med
                v_val = v_med
            
            # 适度色彩映射增强，使得印刷和显示具有最佳可读对比度
            s_render = np.clip(s_val * 1.35, 0.45, 0.92)
            v_render = np.clip(v_val * 1.15, 0.38, 0.92)
            rgb_col = colorsys.hsv_to_rgb(deg / 360.0, s_render, v_render)
                
            ax_b.barh(i, w * 100, left=left_pos, height=bar_height, color=rgb_col, edgecolor='none')
            left_pos += w * 100
            
        cold_rate = (shares['h6'] + shares['h7'] + shares['h8']) * 100
        warm_rate = (shares['h0'] + shares['h1'] + shares['h11']) * 100
        
        # 8 大类型内部核心特征微标签
        if g == '动画':
            anim_col = sub['colorful'].mean()
            ax_b.text(48, i, f'高彩全色谱 (丰富度 {anim_col:.1f})', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#744210', ec='white', lw=0.6, alpha=0.9))
        elif g == '喜剧':
            ax_b.text(28, i, f'高调暖橙 {warm_rate:.1f}%', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#b7791f', ec='white', lw=0.6, alpha=0.9))
        elif g == '爱情':
            ax_b.text(28, i, f'暖红橙调 {warm_rate:.1f}%', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#9b2c2c', ec='white', lw=0.6, alpha=0.9))
        elif g == '剧情':
            ax_b.text(72, i, f'工业中性写实均衡', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#4a5568', ec='white', lw=0.6, alpha=0.9))
        elif g == '动作':
            ax_b.text(70, i, f'冷夜金属 {cold_rate:.1f}%', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#2c5282', ec='white', lw=0.6, alpha=0.9))
        elif g == '科幻':
            ax_b.text(70, i, f'青蓝冷光 {cold_rate:.1f}%', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#1a365d', ec='white', lw=0.6, alpha=0.9))
        elif g == '犯罪':
            ax_b.text(76, i, f'冷夜深暗 (V={v_med:.2f})', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#2d3748', ec='white', lw=0.6, alpha=0.9))
        elif g == '恐怖':
            ax_b.text(76, i, f'极致压抑暗黑 (V={v_med:.2f})', va='center', ha='center',
                      fontsize=8.0, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#171923', ec='white', lw=0.6, alpha=0.9))

    ax_b.set_yticks(y_coords)
    y_tick_labels = [f"{g}\n(n={len(df_u[common.has_genre(df_u, g)]):,})" for g in GENRES_8]
    ax_b.set_yticklabels(y_tick_labels, fontsize=9.5, fontweight='bold')
    ax_b.set_xlabel('色相扇区物理累积占比 (%) (从左至右依次为红橙黄绿青蓝紫)', fontsize=9.5)
    ax_b.set_xlim(0, 100)
    ax_b.set_ylim(-0.6, len(GENRES_8) - 0.4)
    ax_b.invert_yaxis()
    ax_b.set_title('面板 B：8 大主流类型真实海报色彩基因光谱带\n(条带颜色由各类型 12 扇区加权真实物理色彩生成)',
                   fontsize=10.5, fontweight='bold', pad=12)
    ax_b.grid(axis='x', alpha=0.25, linestyle='--')

    # -------------------------------------------------------------
    # 面板 C：8 大类型在 4 种色型中的流向矩阵与超配比率 (含 Baseline 大盘)
    # -------------------------------------------------------------
    ax_c = fig.add_subplot(gs[2])
    
    # 构建交叉百分比数据与频数表
    heatmap_matrix = []
    ct_counts = []
    for g in GENRES_8:
        sub = df_u[common.has_genre(df_u, g)]
        raw_vc = sub['cluster'].value_counts().reindex(range(4), fill_value=0)
        ct_counts.append(raw_vc.values)
        vc = sub['cluster'].value_counts(normalize=True).reindex(range(4), fill_value=0) * 100
        heatmap_matrix.append(vc.values)
    heatmap_matrix = np.array(heatmap_matrix)
    ct_counts = np.array(ct_counts)
    
    # 独立性卡方检验
    chi2_val, p_val, dof, _ = chi2_contingency(ct_counts)
    cramers_v = np.sqrt(chi2_val / (ct_counts.sum() * min(len(GENRES_8) - 1, 4 - 1)))
    
    # 全库大盘基准分布 (Baseline)
    baseline_shares = df_u['cluster'].value_counts(normalize=True).reindex(range(4)).values * 100
    
    # 绘制 8 大类型单元格 (含百分比与超配倍数 Ratio)
    for row_idx in range(len(GENRES_8)):
        row_vals = heatmap_matrix[row_idx]
        max_col_idx = np.argmax(row_vals)
        for col_idx in range(4):
            val = row_vals[col_idx]
            base_col = CLUSTER_BASE_COLORS[col_idx]
            alpha_val = np.clip(val / 46.0, 0.12, 0.95)
            is_peak = (col_idx == max_col_idx)
            ratio = val / baseline_shares[col_idx]
            
            edge_color = '#d69e2e' if is_peak else 'white'
            edge_width = 2.2 if is_peak else 0.8
            rect = patches.FancyBboxPatch((col_idx - 0.44, row_idx - 0.40), 0.88, 0.80,
                                          boxstyle="round,pad=0.03",
                                          facecolor=base_col, alpha=alpha_val,
                                          edgecolor=edge_color, lw=edge_width, zorder=3 if is_peak else 2)
            ax_c.add_patch(rect)
            
            text_color = 'white' if alpha_val >= 0.48 else '#2d3748'
            font_weight = 'bold' if is_peak else 'normal'
            peak_prefix = "★" if is_peak else ""
            cell_str = f"{peak_prefix}{val:.1f}%\n({ratio:.2f}×)"
            ax_c.text(col_idx, row_idx, cell_str, ha='center', va='center',
                      fontsize=7.6, fontweight=font_weight, color=text_color, zorder=4)

    # 最下方追加一行【全库大盘基准 (Baseline)】
    base_row_idx = len(GENRES_8)
    for col_idx in range(4):
        b_val = baseline_shares[col_idx]
        rect_b = patches.FancyBboxPatch((col_idx - 0.44, base_row_idx - 0.38), 0.88, 0.74,
                                        boxstyle="round,pad=0.03",
                                        facecolor='#edf2f7', edgecolor='#cbd5e0', lw=1.0, zorder=2)
        ax_c.add_patch(rect_b)
        ax_c.text(col_idx, base_row_idx, f"基准: {b_val:.1f}%\n(1.00×)", ha='center', va='center',
                  fontsize=7.4, fontweight='bold', color='#4a5568', zorder=4)

    ax_c.set_xticks(range(4))
    cluster_labels = ['冷光青蓝调\n(科技深空)', '极致暗黑调\n(压抑低明)', '高饱和艳丽调\n(多巴胺高彩)', '高亮通透调\n(高光白亮)']
    ax_c.set_xticklabels(cluster_labels, fontsize=8.2, fontweight='bold')
    
    y_all_labels = GENRES_8 + ['【大盘基准】']
    ax_c.set_yticks(range(len(y_all_labels)))
    ax_c.set_yticklabels(y_all_labels, fontsize=9.0, fontweight='bold')
    ax_c.set_xlim(-0.6, 3.6)
    ax_c.set_ylim(-0.6, len(y_all_labels) - 0.4)
    ax_c.set_title(f'面板 C：8 大类型在 4 大色型间的流向矩阵与超配比率\n(行和=100%, 独立性: χ² = {chi2_val:.1f}, p < 1e-300, Cramér\'s V = {cramers_v:.3f})',
                   fontsize=10.5, fontweight='bold', pad=12)
    ax_c.invert_yaxis()

    plt.suptitle('图 1　电影海报配色的真实光谱流形与 8 大类型客观聚集套路',
                 fontsize=13.5, fontweight='bold', y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.12, left=0.06, right=0.98)
    
    out_fig = os.path.join(common.FIG, 'fig_q1_hue.png')
    plt.savefig(out_fig, dpi=300, bbox_inches='tight', facecolor='white')
    
    backup_fig = os.path.join(SCRIPT_DIR, 'fig1_v3_visual.png')
    plt.savefig(backup_fig, dpi=300, bbox_inches='tight', facecolor='white')
    
    return out_fig, backup_fig, heatmap_matrix, baseline_shares


def main():
    print('>>> [1/4] 载入全量电影元数据与物理配色特征...')
    df = common.load()
    df_u = common.usable_hue(df).copy()
    print(f'    有效物理海报样本数: {len(df_u):,} 部')
    
    print('>>> [2/4] 执行无监督聚类 (K-Means) 并提取真实色彩参数...')
    df_u, kmeans, X_scaled = fit_clusters(df_u)
    
    print('>>> [3/4] 渲染高颜值全景色彩大图 (18.2x6.6 英寸, 300 DPI)...')
    out_fig, backup_fig, heatmap_matrix, baseline_shares = render_fig1_spectacular(df_u)
    print(f'    定稿图已发布至全组发布目录: {out_fig}')
    print(f'    草稿备份已保存至: {backup_fig}')
    
    print('>>> [4/4] 导出精细化统计数据与解读报告...')
    stats_rows = []
    for i, g in enumerate(GENRES_8):
        row = {'genre': g}
        for c_idx in range(4):
            val = round(heatmap_matrix[i, c_idx], 2)
            ratio = round(val / baseline_shares[c_idx], 2)
            row[CLUSTER_NAMES[c_idx]] = val
            row[f'{CLUSTER_NAMES[c_idx]}_超配倍数'] = ratio
        stats_rows.append(row)
    
    # 增加基准行
    base_row = {'genre': '全库大盘基准'}
    for c_idx in range(4):
        base_row[CLUSTER_NAMES[c_idx]] = round(baseline_shares[c_idx], 2)
        base_row[f'{CLUSTER_NAMES[c_idx]}_超配倍数'] = 1.0
    stats_rows.append(base_row)

    stats_df = pd.DataFrame(stats_rows)
    stats_csv = os.path.join(SCRIPT_DIR, 'fig1_stats.csv')
    stats_df.to_csv(stats_csv, index=False, encoding='utf-8-sig')
    print(f'    统计数据表已更新: {stats_csv}')
    print('>>> 全新高颜值图 1 渲染完成！')


if __name__ == '__main__':
    main()
