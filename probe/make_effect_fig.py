#!/usr/bin/env python3
"""一张图说清两件事：
左：把 zh 海报换成原语言海报，特征变化有多大（和「同语言换一张」对照）
右：现有海报是 zh 的比例，按年代
"""
import csv, os
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['STHeiti', 'Songti SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs', 'a')


def main():
    rows = list(csv.DictReader(open(os.path.join(OUT, 'feature_delta.csv'), encoding='utf-8')))
    zh = [abs(float(r['mean_v'])) for r in rows if r['group'] == 'zh']
    ctrl = [abs(float(r['mean_v'])) for r in rows if r['group'] == 'ctrl']

    sample = list(csv.DictReader(open(os.path.join(OUT, 'poster_sample.csv'), encoding='utf-8')))
    tab = defaultdict(lambda: [0, 0])
    for r in sample:
        d = int(r['year']) // 10 * 10
        tab[d][0] += 1
        if r['cur_lang'] == 'zh':
            tab[d][1] += 1
    dec = sorted(tab)
    share = [tab[d][1] / tab[d][0] for d in dec]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={'width_ratios': [1.15, 1]})
    bins = np.linspace(0, 0.55, 23)
    ax1.hist(ctrl, bins=bins, alpha=.55, label=f'同语言换一张（对照, n={len(ctrl)}）',
             color='#a0aec0', edgecolor='white')
    ax1.hist(zh, bins=bins, alpha=.65, label=f'中文版→原语言版（n={len(zh)}）',
             color='#c53030', edgecolor='white')
    ax1.set_xlabel('换图后平均明度 mean_v 的变化量 |Δ|')
    ax1.set_ylabel('电影数')
    ax1.set_title('换一张海报，特征就变这么多')
    ax1.legend(frameon=False, fontsize=9)
    ax1.spines[['top', 'right']].set_visible(False)

    ax2.bar([f'{d}s' for d in dec], share, color='#c53030', width=.62)
    for i, s in enumerate(share):
        ax2.text(i, s + .02, f'{s:.0%}', ha='center', fontsize=9)
    ax2.set_ylim(0, .85)
    ax2.set_ylabel('现有海报语言 = zh 的比例')
    ax2.set_title('中文海报占比：越新的片越高')
    ax2.spines[['top', 'right']].set_visible(False)
    plt.tight_layout()
    p = os.path.join(OUT, 'poster_lang_effect.png')
    plt.savefig(p, dpi=180)
    print('→', p)


if __name__ == '__main__':
    main()
