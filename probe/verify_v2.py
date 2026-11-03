#!/usr/bin/env python3
"""v2 数据体检：文件完整性 + 特征合法性 + 覆盖率。"""
import csv, os
from collections import Counter

import numpy as np
import pandas as pd
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')


def main():
    plan = pd.read_csv(os.path.join(OUT, 'poster_plan_v2.csv'), dtype={'id': str})
    print('计划行数', len(plan))
    print('动作分布:\n', plan.action.value_counts().to_string())
    print('\n现状语言分布:\n', plan.cur_lang.value_counts().head(12).to_string())

    # 1) 文件完整性
    v2 = os.path.join(OUT, 'posters_v2')
    files = sorted(f for f in os.listdir(v2) if f.endswith('.jpg')) if os.path.exists(v2) else []
    print(f'\nposters_v2 文件数 {len(files)}')
    small, bad = [], []
    for i, fn in enumerate(files):
        p = os.path.join(v2, fn)
        if os.path.getsize(p) < 2000:
            small.append(fn)
            continue
        if i % 5 == 0:                       # 五分之一做解码检查
            try:
                with Image.open(p) as im:
                    im.verify()
            except Exception:
                bad.append(fn)
    print(f'  小于 2KB: {len(small)}   解码失败(抽 1/5): {len(bad)}')
    if bad:
        print('  坏文件示例:', bad[:5])

    # 2) 尺寸
    dims = Counter()
    for fn in files[::10]:
        with Image.open(os.path.join(v2, fn)) as im:
            dims[im.size] += 1
    print('  尺寸分布(抽 1/10):', dims.most_common(5))

    # 3) 特征表
    fp = os.path.join(OUT, 'color_features_v2.csv')
    if not os.path.exists(fp):
        print('\n特征表还没生成')
        return
    f = pd.read_csv(fp)
    print(f'\n特征表 {len(f)} 行')
    print('  重复 id:', int(f.tmdb_id.duplicated().sum()))
    for c in ['mean_s', 'mean_v', 'v_std', 'sat_frac', 'colorful']:
        v = f[c]
        print(f'  {c:10s} 缺失 {int(v.isna().sum()):5d}  范围 [{v.min():.3f}, {v.max():.3f}]  '
              f'中位 {v.median():.3f}')
    hcols = [f'h{i}' for i in range(12)]
    s = f[hcols].sum(1)
    print(f'  色相扇区和: 应≈1，实际 [{s.min():.3f}, {s.max():.3f}]')
    print(f'  sat_frac<0.10（近乎灰、色相不可用）: {int((f.sat_frac < 0.10).sum())} 行')

    # 4) 覆盖率
    m = pd.concat([pd.read_csv(os.path.join(DATA, 'movies.csv')),
                   pd.read_csv(os.path.join(OUT, 'era_expansion.csv'))], ignore_index=True)
    m['decade'] = (m.year // 10 * 10).astype(int)
    merged = m.merge(f, left_on='id', right_on='tmdb_id', how='left')
    tab = merged.groupby('decade').agg(n=('id', 'size'), ok=('mean_v', 'count'))
    tab['覆盖率'] = (tab.ok / tab.n).round(3)
    print('\n各年代覆盖率:')
    print(tab.to_string())


if __name__ == '__main__':
    main()
