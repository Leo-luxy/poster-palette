#!/usr/bin/env python3
"""对比 v1（现状）与 v2（原语言海报 + 每年前 2.6% 补片）的年代趋势。"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams['font.sans-serif'] = ['STHeiti', 'Songti SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')


def load(v2=False):
    m = pd.read_csv(os.path.join(DATA, 'movies.csv'))
    exp = os.path.join(OUT, 'era_expansion.csv')
    if v2 and os.path.exists(exp):
        m = pd.concat([m, pd.read_csv(exp)], ignore_index=True)
    f = pd.read_csv(os.path.join(OUT, 'color_features_v2.csv' if v2 else os.path.join(DATA, 'color_features.csv')))
    df = m.merge(f, left_on='id', right_on='tmdb_id')
    df['decade'] = (df.year // 10 * 10).astype(int)
    return df


def main():
    a, b = load(False), load(True)
    print('v1 行数', len(a), '  v2 行数', len(b))
    print('\n年代   v1 n   v1 mean_v   v2 n   v2 mean_v   Δ')
    for d in sorted(set(a.decade) & set(b.decade)):
        ga, gb = a[a.decade == d], b[b.decade == d]
        print(f'{d}s  {len(ga):5d}   {ga.mean_v.mean():.3f}     {len(gb):5d}   '
              f'{gb.mean_v.mean():.3f}   {gb.mean_v.mean()-ga.mean_v.mean():+.3f}')

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, col, title in zip(axes, ['mean_v', 'mean_s', 'sat_frac'],
                              ['平均明度', '平均饱和度', '高饱和像素占比']):
        for df, lab, c in ((a, 'v1 现状', '#a0aec0'), (b, 'v2 原语言+补片', '#c53030')):
            g = df.groupby('decade')[col].mean()
            n = df.groupby('decade')[col].count()
            ax.plot(g.index, g.values, 'o-', label=f'{lab}', color=c)
        ax.set_title(title)
        ax.set_xlabel('年代')
        ax.legend(frameon=False, fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)
    plt.tight_layout()
    p = os.path.join(OUT, 'v1_vs_v2.png')
    plt.savefig(p, dpi=180)
    print('\n→', p)


if __name__ == '__main__':
    main()
