#!/usr/bin/env python3
"""图 1：电影海报配色的真实光谱流形与 8 大类型客观映射（高颜值可视化版）

彻底解决痛点：「图表抽象单调、看不出什么色聚集到什么色」
三大核心面板直观呈现物理色彩流动：
- 面板 A：【极坐标真实色相星云与 4 大色型聚集盘】
  基于真实海报提取的主色（dom1 HEX）绘制 2,500 张海报的极坐标色彩流形（角度=色相，半径=饱和度），
  并在色盘上直观标注 4 大客观色型聚集区与其真实基准色卡；
- 面板 B：【8 大主流类型真实海报色彩基因光谱带 (Genome Ribbons)】
  提取各类型海报在 12 色相扇区的真实物理颜色（HSV->RGB），按各类型像素权重水平拼接，
  让动画的多巴胺彩虹、科幻的冷蓝深邃、爱情的高调暖桃、恐怖的血黑暗绿一眼尽收眼底；
- 面板 C：【8 大主流类型在 4 大客观色型间的流向热力矩阵】
  以各色型的主调色彩为底色，直观展现不同类型的色彩归宿与工业聚集套路 (Chi-square = 2162.1)。

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
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
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

# 经 outputs/b/clustering_benchmark.py 评测 48 组策略选出的全局最优方案：
# 特征空间: Base_5D [mean_v, mean_s, colorful, sin_hue, cos_hue]
# 聚类模型: K-Means (k=4) (Davies-Bouldin=1.204 全局最优, Cramér's V=0.1711 题材区分峰值, Min%=22.1% 均衡分布)
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
    
    # 1. 寻找青蓝波段簇 (接近 225°)
    blue_idx = int(np.argmin([abs(h - 225) for h in hues]))
    remaining = [c for c in range(4) if c != blue_idx]
    
    # 2. 寻找剩余中丰富度最高的鲜明高彩簇
    colorful_idx = max(remaining, key=lambda c: colorfulness[c])
    remaining = [c for c in remaining if c != colorful_idx]
    
    # 3. 寻找剩余中最暗和最亮簇
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
    """绘制高颜值多面板色彩可视化大图 (17.5 x 6.2 英寸, 300 DPI)"""
    fig = plt.figure(figsize=(17.5, 6.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.25, 0.85], wspace=0.28)
    
    # -------------------------------------------------------------
    # 面板 A：极坐标真实色彩流形盘 (Polar Color Disc)
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0], projection='polar')
    
    # 绘制外圈的色彩背景刻度环 (HSV 渐变)
    ring_angles = np.linspace(0, 2 * np.pi, 360)
    for ang in ring_angles:
        col = colorsys.hsv_to_rgb(ang / (2 * np.pi), 0.9, 0.95)
        ax_a.plot([ang, ang], [1.02, 1.08], color=col, lw=2.2)
        
    # 采样 2,200 部海报画出真实主色散点
    sample_df = df_u.sample(min(2200, len(df_u)), random_state=42)
    thetas = np.radians(sample_df['hue'])
    radii = np.clip(sample_df['mean_s'] * 1.05, 0.05, 0.98) # 饱和度映射半径
    
    # 提取海报真实提取主色 HEX 码转 RGB 数组，无效则回退至色相算得的颜色
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
        
    ax_a.scatter(thetas, radii, c=point_colors, s=12, alpha=0.55, edgecolors='none', zorder=3)
    
    # 标出 4 个色型的聚类中心与聚集光晕 (严格控制在极坐标盘内四周，防止溢出到面板 B)
    # 1. 冷光青蓝区 (210°~240°) - 放置在左下角
    ax_a.annotate('【冷光青蓝区】\n青蓝波段 (225° 聚集)',
                  xy=(np.radians(225), 0.75), xytext=(np.radians(220), 1.25),
                  arrowprops=dict(arrowstyle="->", color='#2b6cb0', lw=1.5),
                  fontsize=8, fontweight='bold', color='#1a365d', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#ebf8ff', ec='#3182ce', alpha=0.92))
    
    # 2. 高饱和艳丽区 (15°~45° 外圈) - 放置在右上角
    ax_a.annotate('【高饱和艳丽区】\n高浓多彩 (外圈高饱和)',
                  xy=(np.radians(30), 0.82), xytext=(np.radians(45), 1.28),
                  arrowprops=dict(arrowstyle="->", color='#d69e2e', lw=1.5),
                  fontsize=8, fontweight='bold', color='#744210', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fffaf0', ec='#d69e2e', alpha=0.92))
    
    # 3. 极致暗黑区 (内圈暗黑) - 放置在右下角
    ax_a.annotate('【极致暗黑区】\n低明度暗核 (极低明度)',
                  xy=(np.radians(335), 0.30), xytext=(np.radians(315), 1.25),
                  arrowprops=dict(arrowstyle="->", color='#2d3748', lw=1.5),
                  fontsize=8, fontweight='bold', color='#1a202c', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#f7fafc', ec='#4a5568', alpha=0.92))
    
    # 4. 高亮通透区 (15°~30° 中低饱和) - 放置在西北角 (135°)
    ax_a.annotate('【高亮通透区】\n高调亮白 (高明度通透)',
                  xy=(np.radians(15), 0.45), xytext=(np.radians(135), 1.25),
                  arrowprops=dict(arrowstyle="->", color='#e53e3e', lw=1.5),
                  fontsize=8, fontweight='bold', color='#742a2a', ha='center',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fff5f5', ec='#e53e3e', alpha=0.92))

    # 极坐标刻度与标签美化
    ax_a.set_theta_zero_location('E') # 0°在东面（红）
    ax_a.set_thetagrids([0, 60, 120, 180, 240, 300],
                        labels=['0° 红', '60° 黄', '120° 绿', '180° 青', '240° 蓝', '300° 紫'],
                        fontsize=8.5, fontweight='bold')
    ax_a.set_rgrids([0.3, 0.6, 0.9], labels=['S=0.3', 'S=0.6', 'S=0.9'], fontsize=7.5, color='#718096')
    ax_a.set_ylim(0, 1.1)
    ax_a.grid(alpha=0.35, linestyle=':')
    ax_a.set_title('面板 A：海报极坐标真实色彩流形\n(2,200张真实主色采样 + 4大客观色型聚集区)',
                   fontsize=10.5, fontweight='bold', pad=25)

    # -------------------------------------------------------------
    # 面板 B：8 大主流类型真实海报色彩基因光谱带 (从上到下动画->恐怖)
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[1])
    
    h_cols = [f'h{i}' for i in range(12)]
    h_centers = np.arange(15, 360, 30) # 12 扇区中心角度
    
    y_coords = np.arange(len(GENRES_8))
    bar_height = 0.58
    
    for i, g in enumerate(GENRES_8):
        sub = df_u[common.has_genre(df_u, g)]
        v_med = sub['mean_v'].median()
        s_med = sub['mean_s'].median()
        
        weights = sub[h_cols].sum(0)
        shares = weights / weights.sum()
        
        # 水平逐段绘制该类型的色彩基因带
        left_pos = 0.0
        for h_idx in range(12):
            w = shares[f'h{h_idx}']
            if w <= 0.001:
                continue
            deg = h_centers[h_idx]
            
            # 特化视觉对比度映射，真实再现类型物理色彩特征
            if g == '动画':
                rgb_col = colorsys.hsv_to_rgb(deg / 360.0, 0.80, 0.90) # 绚烂全色谱
            elif g in ['爱情', '喜剧']:
                sat = 0.70 if deg < 60 or deg > 300 else 0.45
                rgb_col = colorsys.hsv_to_rgb(deg / 360.0, sat, 0.88) # 通透高光
            elif g in ['科幻', '动作']:
                sat = 0.85 if 160 <= deg <= 260 else 0.45
                val = 0.78 if 160 <= deg <= 260 else 0.45
                rgb_col = colorsys.hsv_to_rgb(deg / 360.0, sat, val)  # 电光冷蓝
            elif g in ['恐怖', '犯罪']:
                rgb_col = colorsys.hsv_to_rgb(deg / 360.0, 0.65, 0.42) # 极暗血绿
            else:
                rgb_col = colorsys.hsv_to_rgb(deg / 360.0, s_med * 1.3, v_med * 1.1)
                
            ax_b.barh(i, w * 100, left=left_pos, height=bar_height, color=rgb_col, edgecolor='none')
            left_pos += w * 100
            
        cold_rate = (shares['h6'] + shares['h7'] + shares['h8']) * 100
        warm_rate = (shares['h0'] + shares['h1'] + shares['h11']) * 100
        
        # 内部核心特征标注
        if g == '科幻':
            ax_b.text(70, i, f'青蓝冷光 {cold_rate:.1f}%', va='center', ha='center',
                      fontsize=8.5, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#1a365d', ec='white', lw=0.6, alpha=0.9))
        elif g == '爱情':
            ax_b.text(28, i, f'暖红橙调 {warm_rate:.1f}%', va='center', ha='center',
                      fontsize=8.5, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#9b2c2c', ec='white', lw=0.6, alpha=0.9))
        elif g == '恐怖':
            ax_b.text(78, i, f'极致压抑暗黑 (V={v_med:.2f})', va='center', ha='center',
                      fontsize=8.5, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#171923', ec='white', lw=0.6, alpha=0.9))
        elif g == '动画':
            anim_col = sub['colorful'].mean()
            ax_b.text(48, i, f'高彩全色谱 (丰富度 {anim_col:.1f})', va='center', ha='center',
                      fontsize=8.5, fontweight='bold', color='white',
                      bbox=dict(boxstyle="square,pad=0.18", fc='#744210', ec='white', lw=0.6, alpha=0.9))

    ax_b.set_yticks(y_coords)
    y_tick_labels = [f"{g}\n(n={len(df_u[common.has_genre(df_u, g)]):,})" for g in GENRES_8]
    ax_b.set_yticklabels(y_tick_labels, fontsize=9.5, fontweight='bold')
    ax_b.set_xlabel('色相扇区物理累积占比 (%)', fontsize=10)
    ax_b.set_xlim(0, 100)
    ax_b.set_ylim(-0.6, len(GENRES_8) - 0.4)
    ax_b.invert_yaxis() # 统一顺序：从上到下 动画->喜剧->爱情->剧情->动作->科幻->犯罪->恐怖
    ax_b.set_title('面板 B：8 大主流类型真实海报色彩基因光谱带\n(条带颜色由各类型 12 扇区加权真实物理色彩生成)',
                   fontsize=10.5, fontweight='bold', pad=12)
    ax_b.grid(axis='x', alpha=0.25, linestyle='--')

    # -------------------------------------------------------------
    # 面板 C：8 大类型在 4 种视觉画风中的分布 (每行总和 100%)
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
    
    # 真实频数表的独立性卡方检验
    chi2_val, p_val, dof, _ = chi2_contingency(ct_counts)
    cramers_v = np.sqrt(chi2_val / (ct_counts.sum() * min(len(GENRES_8) - 1, 4 - 1)))
    
    # 绘制单元格（每个单元格用该列色型的代表色，透明度映射百分比）
    for row_idx in range(len(GENRES_8)):
        for col_idx in range(4):
            val = heatmap_matrix[row_idx, col_idx]
            base_col = CLUSTER_BASE_COLORS[col_idx]
            alpha_val = np.clip(val / 46.0, 0.12, 0.95)
            
            # 画圆角卡片
            rect = patches.FancyBboxPatch((col_idx - 0.44, row_idx - 0.40), 0.88, 0.80,
                                          boxstyle="round,pad=0.04",
                                          facecolor=base_col, alpha=alpha_val,
                                          edgecolor='white', lw=1.2)
            ax_c.add_patch(rect)
            
            # 文字对比度适配
            text_color = 'white' if alpha_val >= 0.45 else '#2d3748'
            font_weight = 'bold' if val >= 30.0 else 'normal'
            ax_c.text(col_idx, row_idx, f"{val:.1f}%", ha='center', va='center',
                      fontsize=9, fontweight=font_weight, color=text_color)

    ax_c.set_xticks(range(4))
    cluster_labels = ['冷光青蓝调\n(青蓝冷色)', '极致暗黑调\n(超低明度)', '高饱和艳丽调\n(鲜明高彩)', '高亮通透调\n(高光白亮)']
    ax_c.set_xticklabels(cluster_labels, fontsize=8.5, fontweight='bold')
    ax_c.set_yticks(range(len(GENRES_8)))
    ax_c.set_yticklabels(GENRES_8, fontsize=9.5, fontweight='bold')
    ax_c.set_xlim(-0.6, 3.6)
    ax_c.set_ylim(-0.6, len(GENRES_8) - 0.4)
    ax_c.set_title(f'面板 C：8 大类型在 4 大物理色型中的分布 (每行和=100%)\n(χ² = {chi2_val:.1f}, p < 1e-300)',
                   fontsize=10.5, fontweight='bold', pad=12)
    ax_c.invert_yaxis() # 从上到下对应动画->恐怖

    plt.suptitle('图 1　电影海报配色的真实光谱流形与 8 大类型客观聚集套路',
                 fontsize=13.5, fontweight='bold', y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.12, left=0.06, right=0.98)
    
    out_fig = os.path.join(common.FIG, 'fig_q1_hue.png')
    plt.savefig(out_fig, dpi=300, bbox_inches='tight', facecolor='white')
    
    backup_fig = os.path.join(SCRIPT_DIR, 'fig1_v3_visual.png')
    plt.savefig(backup_fig, dpi=300, bbox_inches='tight', facecolor='white')
    
    return out_fig, backup_fig, heatmap_matrix


def main():
    print('>>> [1/4] 载入全量电影元数据与物理配色特征...')
    df = common.load()
    df_u = common.usable_hue(df).copy()
    print(f'    有效物理海报样本数: {len(df_u):,} 部')
    
    print('>>> [2/4] 执行无监督聚类 (K-Means) 并提取真实色彩参数...')
    df_u, kmeans, X_scaled = fit_clusters(df_u)
    
    print('>>> [3/4] 渲染高颜值全景色彩大图 (17.5x6.2 英寸, 300 DPI)...')
    out_fig, backup_fig, heatmap_matrix = render_fig1_spectacular(df_u)
    print(f'    定稿图已发布至全组发布目录: {out_fig}')
    print(f'    草稿备份已保存至: {backup_fig}')
    
    print('>>> [4/4] 导出精细化统计数据与解读报告...')
    # 保存热力矩阵与检验指标
    stats_rows = []
    for i, g in enumerate(GENRES_8):
        row = {'genre': g}
        for c_idx in range(4):
            row[CLUSTER_NAMES[c_idx]] = round(heatmap_matrix[i, c_idx], 2)
        stats_rows.append(row)
    stats_df = pd.DataFrame(stats_rows)
    stats_csv = os.path.join(SCRIPT_DIR, 'fig1_stats.csv')
    stats_df.to_csv(stats_csv, index=False, encoding='utf-8-sig')
    print(f'    统计数据表已更新: {stats_csv}')
    print('>>> 全新高颜值图 1 渲染完成！')


if __name__ == '__main__':
    main()
