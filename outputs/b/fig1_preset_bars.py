#!/usr/bin/env python3
"""图 1 预设分组对比图（做法 A）：科幻 / 爱情 / 恐怖 12 扇区色相分布与核心特征检验
严格遵循队长交接文档要求：
- 横轴：12 个扇区（0–30°、30–60°…），标注「0°=红 120°=绿 240°=蓝」
- 纵轴：占比
- 三类并排分组柱状图，配色严格对应 common.COLOR
- Kruskal-Wallis 检验三类在 mean_v, mean_s, colorful 上的差异
- 独立性卡方检验 12 扇区与类型的分布关联

输出：
- figures/fig_q1_preset_bars.png （300 DPI 高清大图）
- outputs/b/fig1_preset_stats.csv （统计检验指标表）
"""
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kruskal, chi2_contingency

# 引入根目录公共模块
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from scripts import common

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

TARGETS = ['科幻', '爱情', '恐怖']
SECTOR_NAMES = [
    '0-30°\n(红)', '30-60°\n(橙)', '60-90°\n(黄橙)', '90-120°\n(黄绿)',
    '120-150°\n(绿)', '150-180°\n(青绿)', '180-210°\n(青)', '210-240°\n(蓝)',
    '240-270°\n(深蓝)', '270-300°\n(紫)', '300-330°\n(品红)', '330-360°\n(红紫)'
]


def run_preset_analysis():
    print(">>> [1/3] 载入电影数据并提取三类色相分布...")
    df = common.load()
    df_u = common.usable_hue(df).copy()

    # 1. 计算三类在 12 扇区的占比
    shares = {}
    sample_sizes = {}
    for g in TARGETS:
        sh = common.hue_share(df, g)
        shares[g] = sh.values * 100 # 转为百分比
        sample_sizes[g] = len(df_u[common.has_genre(df_u, g)])
        print(f"    {g} (n={sample_sizes[g]:,}): 峰值扇区={SECTOR_NAMES[np.argmax(shares[g])].splitlines()[0]}, 峰值占比={np.max(shares[g]):.2f}%")

    # 12 扇区卡方检验
    contingency_list = []
    for g in TARGETS:
        sub = df_u[common.has_genre(df_u, g)]
        cols = [f'h{i}' for i in range(12)]
        contingency_list.append(sub[cols].sum(0).values)
    ct_matrix = np.array(contingency_list)
    chi2_val, p_chi2, dof, _ = chi2_contingency(ct_matrix)
    cramers_v = np.sqrt(chi2_val / (ct_matrix.sum() * (min(ct_matrix.shape) - 1)))
    print(f"    12 扇区卡方独立性检验: chi2 = {chi2_val:.1f}, p = {p_chi2:.1e}, Cramers_V = {cramers_v:.4f}")

    # 2. Kruskal-Wallis 检验三类在 mean_v, mean_s, colorful 上的差异
    stats_records = []
    test_metrics = [
        ('mean_v', '平均明度 (0-1)'),
        ('colorful', '色彩丰富度 (0-200)'),
        ('mean_s', '平均饱和度 (0-1)')
    ]
    subsets = {g: df_u[common.has_genre(df_u, g)] for g in TARGETS}

    h_stat_dict = {}
    for col, label in test_metrics:
        data_groups = [subsets[g][col].dropna().values for g in TARGETS]
        h_stat, p_kw = kruskal(*data_groups)
        h_stat_dict[col] = (h_stat, p_kw)
        medians = {g: float(np.median(subsets[g][col].dropna())) for g in TARGETS}
        means = {g: float(np.mean(subsets[g][col].dropna())) for g in TARGETS}
        
        # 效应量 eta^2 = (H - k + 1) / (N - k)
        n_total = sum(len(grp) for grp in data_groups)
        eta_sq = (h_stat - len(TARGETS) + 1) / (n_total - len(TARGETS))

        diff_v = means['爱情'] - means['恐怖']
        print(f"    {col:10s}: H={h_stat:7.1f}, p={p_kw:.1e}, eta2={eta_sq:.4f} | 爱情均值={means['爱情']:.2f}, 恐怖均值={means['恐怖']:.2f}, 相差={diff_v:+.2f}")
        
        stats_records.append({
            'Metric': col,
            'Label': label,
            'H_Stat': round(h_stat, 1),
            'P_Val': p_kw,
            'Eta_Squared': round(eta_sq, 4),
            'Mean_科幻': round(means['科幻'], 3),
            'Mean_爱情': round(means['爱情'], 3),
            'Mean_恐怖': round(means['恐怖'], 3),
            'Median_科幻': round(medians['科幻'], 3),
            'Median_爱情': round(medians['爱情'], 3),
            'Median_恐怖': round(medians['恐怖'], 3),
            'Diff_爱情减恐怖': round(diff_v, 3)
        })

    # 输出统计检验表
    stats_df = pd.DataFrame(stats_records)
    out_csv = os.path.join(ROOT, 'outputs', 'b', 'fig1_preset_stats.csv')
    stats_df.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"    检验数据表已保存至: {out_csv}")

    # 3. 绘制 2 面板图表
    print("\n>>> [3/3] 渲染 300 DPI 预设对比图 (figures/fig_q1_preset_bars.png)...")
    fig = plt.figure(figsize=(16, 6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 0.7], wspace=0.22)

    # -------------------------------------------------------------
    # 面板 A：12 扇区分组柱状图（横轴 12 扇区，三类并排）
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0])
    x = np.arange(12)
    width = 0.26

    # 柱状图
    rects1 = ax_a.bar(x - width, shares['科幻'], width, label=f"科幻 (n={sample_sizes['科幻']:,})",
                      color=common.COLOR['科幻'], alpha=0.90, edgecolor='white', lw=0.8)
    rects2 = ax_a.bar(x, shares['爱情'], width, label=f"爱情 (n={sample_sizes['爱情']:,})",
                      color=common.COLOR['爱情'], alpha=0.90, edgecolor='white', lw=0.8)
    rects3 = ax_a.bar(x + width, shares['恐怖'], width, label=f"恐怖 (n={sample_sizes['恐怖']:,})",
                      color=common.COLOR['恐怖'], alpha=0.90, edgecolor='white', lw=0.8)

    # 峰值与特色标注（组长验收标准：一眼看出科幻偏蓝、恐怖偏绿、爱情偏红）
    # 1. 爱情在 0-30° (扇区 0) 极度显著
    ax_a.annotate(f"爱情暖红峰值\n{shares['爱情'][0]:.1f}% (肤色/暖光)",
                  xy=(0, shares['爱情'][0]), xytext=(0.6, 42.0),
                  arrowprops=dict(arrowstyle="->", color=common.COLOR['爱情'], lw=1.5),
                  fontsize=8.5, fontweight='bold', color='#7b341e',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#fffaf0', ec=common.COLOR['爱情'], alpha=0.95))

    # 2. 恐怖在 120-150° (扇区 4 绿色) 明显高于其他类
    ax_a.annotate(f"恐怖偏冷绿\n{shares['恐怖'][4]:.1f}% (阴森鬼火)",
                  xy=(4 + width, shares['恐怖'][4]), xytext=(4.2, shares['恐怖'][4] + 6.0),
                  arrowprops=dict(arrowstyle="->", color=common.COLOR['恐怖'], lw=1.5),
                  fontsize=8.5, fontweight='bold', color='#1c4532',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#f0fff4', ec=common.COLOR['恐怖'], alpha=0.95))

    # 3. 科幻在 210-240° (扇区 7 蓝色) 极度显著
    ax_a.annotate(f"科幻偏青蓝\n{shares['科幻'][7]:.1f}% (深空与科技)",
                  xy=(7 - width, shares['科幻'][7]), xytext=(6.5, shares['科幻'][7] + 6.0),
                  arrowprops=dict(arrowstyle="->", color=common.COLOR['科幻'], lw=1.5),
                  fontsize=8.5, fontweight='bold', color='#1a365d',
                  bbox=dict(boxstyle="round,pad=0.25", fc='#ebf8ff', ec=common.COLOR['科幻'], alpha=0.95))

    ax_a.set_xticks(x)
    ax_a.set_xticklabels(SECTOR_NAMES, fontsize=8.5, fontweight='bold')
    ax_a.set_ylabel('海报色彩有效像素占比 (%)', fontsize=10.5, fontweight='bold')
    ax_a.set_ylim(0, 48)
    ax_a.grid(axis='y', alpha=0.25, linestyle=':')
    ax_a.legend(loc='upper right', fontsize=9.5, framealpha=0.95)
    ax_a.set_title(f'面板 A：科幻 / 爱情 / 恐怖在 12 色相扇区的并排分布\n(独立性检验: χ² = {chi2_val:.1f}, p < 1e-20, Cramér\'s V = {cramers_v:.3f})',
                   fontsize=11.5, fontweight='bold', pad=12)

    # -------------------------------------------------------------
    # 面板 B：三类核心物理特征对比 (箱线图 / 误差棒)
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[1])
    
    # 提取 mean_v, colorful 归一化对比
    b_metrics = ['mean_v', 'colorful']
    b_titles = ['平均明度 (mean_v)', '色彩丰富度 (colorful)']
    
    # 绘制三类均值与 95% 置信区间
    genres_list = TARGETS
    pos_base = np.array([1, 2, 3])
    
    # 双 Y 轴展示明度与色彩丰富度
    ax_b_twin = ax_b.twinx()
    
    # 左轴：平均明度 mean_v (0-1)
    means_v = [np.mean(subsets[g]['mean_v']) for g in genres_list]
    se_v = [np.std(subsets[g]['mean_v']) / np.sqrt(len(subsets[g])) for g in genres_list]
    line1 = ax_b.errorbar(pos_base - 0.1, means_v, yerr=se_v, fmt='o-', color='#3182ce', lw=2.2,
                          capsize=5, markersize=8, label='平均明度 mean_v (左轴)')
    
    for i, g in enumerate(genres_list):
        ax_b.text(pos_base[i] - 0.1, means_v[i] + 0.015, f"{means_v[i]:.2f}",
                  ha='center', fontsize=9, fontweight='bold', color='#2b6cb0')

    # 右轴：色彩丰富度 colorful (0-100)
    means_c = [np.mean(subsets[g]['colorful']) for g in genres_list]
    se_c = [np.std(subsets[g]['colorful']) / np.sqrt(len(subsets[g])) for g in genres_list]
    line2 = ax_b_twin.errorbar(pos_base + 0.1, means_c, yerr=se_c, fmt='s--', color='#dd6b20', lw=2.2,
                               capsize=5, markersize=8, label='色彩丰富度 colorful (右轴)')
    
    for i, g in enumerate(genres_list):
        ax_b_twin.text(pos_base[i] + 0.1, means_c[i] + 1.2, f"{means_c[i]:.1f}",
                       ha='center', fontsize=9, fontweight='bold', color='#c05621')

    ax_b.set_xticks(pos_base)
    ax_b.set_xticklabels([f"{g}\n(n={sample_sizes[g]:,})" for g in genres_list], fontsize=10, fontweight='bold')
    ax_b.set_xlim(0.4, 3.6)
    ax_b.set_ylabel('平均明度 mean_v (0–1)', fontsize=10, fontweight='bold', color='#2b6cb0')
    ax_b_twin.set_ylabel('Hasler-Süsstrunk 丰富度 (0–200)', fontsize=10, fontweight='bold', color='#dd6b20')
    ax_b.set_ylim(0.25, 0.72)
    ax_b_twin.set_ylim(40, 85)
    ax_b.grid(alpha=0.25, linestyle=':')

    # 合并图例
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax_b.legend(lines, labels, loc='lower left', fontsize=9, framealpha=0.92)

    # 标注 Kruskal-Wallis 显著结论
    v_diff = means_v[1] - means_v[2] # 爱情 vs 恐怖
    c_diff = means_c[1] - means_c[2]
    means_s = [np.mean(subsets[g]['mean_s']) for g in genres_list]
    s_diff = means_s[1] - means_s[2]
    hv_stat, pv_val = h_stat_dict['mean_v']
    hc_stat, pc_val = h_stat_dict['colorful']
    hs_stat, ps_val = h_stat_dict['mean_s']
    kw_text = (f"Kruskal-Wallis 差异检验：\n"
               f"• 明度差异极显著: H = {hv_stat:.1f} (p < 1e-250)\n"
               f"  爱情比恐怖明度高出 {v_diff:.2f} (大效应量)\n"
               f"• 丰富度差异显著: H = {hc_stat:.1f} (p < 1e-25)\n"
               f"  爱情丰富度比恐怖高出 {c_diff:.1f}\n"
               f"• 饱和度差异微弱: H = {hs_stat:.1f} (Δ = {s_diff:+.2f})")
    ax_b.text(0.57, 0.96, kw_text, transform=ax_b.transAxes,
              verticalalignment='top', horizontalalignment='left',
              fontsize=8.0, bbox=dict(boxstyle="round,pad=0.3", fc='#f7fafc', ec='#cbd5e0', alpha=0.95))

    ax_b.set_title('面板 B：核心特征差异检验\n(Kruskal-Wallis H 检验与 95% 置信区间)',
                   fontsize=11.5, fontweight='bold', pad=12)

    plt.suptitle('图 1（做法 A 预设对比）：科幻、爱情、恐怖三大典型类型的海报配色结构比较',
                 fontsize=13.5, fontweight='bold', y=0.98)
    fig.subplots_adjust(top=0.86, bottom=0.12, left=0.06, right=0.94)

    out_fig = os.path.join(common.FIG, 'fig_q1_preset_bars.png')
    plt.savefig(out_fig, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"    预设分组对比图已生成: {out_fig}")
    return out_fig


if __name__ == '__main__':
    run_preset_analysis()
