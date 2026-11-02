#!/usr/bin/env python3
"""图 3：配色能不能预测口碑？

结论是「不能」——相关系数 |r| < 0.08，几乎为零。
这本身就是要讲的结论：配色是**类型信号**，不是**质量信号**。
注意 p 值会显著（n=1.4 万），但显著 ≠ 有关，报告里必须把这句写上。

输出 figures/fig_q3_score.png + data/fig3_stats.csv
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
GENRES = ['科幻', '爱情', '恐怖', '动作', '喜剧', '剧情', '犯罪', '惊悚']


def r_ci(x, y):
    r, p = pearsonr(x, y)
    n = len(x)
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)          # Fisher z 变换求 95% CI
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return r, p, lo, hi


def main():
    df = common.load()
    df = df[(df.vote_average > 0) & (df.sat_frac > 0)].copy()
    rng = np.random.default_rng(0)
    smp = df.sample(min(4000, len(df)), random_state=0)   # 散点只画采样，避免糊成一团

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), gridspec_kw={'width_ratios': [1, 1, 1.1]})

    # 面板 A / B：散点 + 拟合
    for ax, col, label in [(axes[0], 'mean_v', '平均明度'), (axes[1], 'colorful', '色彩丰富度')]:
        ax.scatter(smp[col], smp['vote_average'], s=6, alpha=.18, c='#4a5568', linewidths=0)
        k, b = np.polyfit(df[col], df['vote_average'], 1)
        xs = np.linspace(df[col].quantile(.01), df[col].quantile(.99), 50)
        ax.plot(xs, k * xs + b, color='#c53030', lw=2.2, label=f'拟合斜率 {k:+.2f}')
        r = pearsonr(df[col], df['vote_average'])[0]
        ax.set_xlabel(label); ax.set_ylabel('TMDB 均分（vote_average）')
        ax.set_title(f'{label} vs 评分　r = {r:+.3f}', fontsize=12)
        ax.legend(loc='lower left', fontsize=9); ax.grid(alpha=.2)
        ax.set_ylim(3, 9.5)

    # 面板 C：各类型相关系数 + 95% CI
    rows = []
    ys = []
    for i, g in enumerate(GENRES):
        sub = df[common.has_genre(df, g)]
        r, p, lo, hi = r_ci(sub.mean_v, sub.vote_average)
        rows.append({'genre': g, 'n': len(sub), 'r_sat': round(pearsonr(sub.mean_s, sub.vote_average)[0], 3),
                     'r_bright': round(r, 3), 'r_colorful': round(pearsonr(sub.colorful, sub.vote_average)[0], 3),
                     'ci_lo': round(lo, 3), 'ci_hi': round(hi, 3), 'p': p})
        ys.append(i)
        axes[2].plot([lo, hi], [i, i], color=common.COLOR.get(g, '#888'), lw=3, alpha=.75,
                     solid_capstyle='round')
        axes[2].plot(r, i, 'o', color=common.COLOR.get(g, '#888'), ms=8)
        axes[2].annotate(f'{r:+.3f}', (hi, i), xytext=(6, -3), textcoords='offset points', fontsize=8.5)
    axes[2].axvline(0, color='#2d3748', ls='--', lw=1.2)
    axes[2].set_yticks(ys); axes[2].set_yticklabels(GENRES)
    axes[2].set_xlabel('明度与评分的相关系数 r（95% 置信区间）')
    axes[2].set_title('分类型看：全部贴着 0', fontsize=12)
    axes[2].grid(axis='x', alpha=.25)
    axes[2].set_xlim(-.25, .25)

    plt.suptitle('图 3　海报配色与口碑：相关系数全在 ±0.08 以内，配色不预测评分', fontsize=14, y=1.02)
    plt.tight_layout()
    out = os.path.join(common.FIG, 'fig_q3_score.png')
    plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='white')

    pd.DataFrame(rows).to_csv(os.path.join(common.DATA, 'fig3_stats.csv'), index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f'\n→ {out}')
    print('提醒：n=1.4 万时 p 值必然显著，报告里要写「显著但效应量近似为零」')


if __name__ == '__main__':
    main()
