#!/usr/bin/env python3
"""年度聚合表：做趋势图的人直接读这两个文件，不用自己 groupby。

data/yearly.csv          每年一行（全类型合计）
data/yearly_by_genre.csv 每年 × 每类型一行
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

def agg(g):
    return pd.Series({
        'n': int(len(g)),
        'med_s': round(float(g.mean_s.median()), 4),
        'med_v': round(float(g.mean_v.median()), 4),
        'med_colorful': round(float(g.colorful.median()), 4),
        'med_vote': round(float(g.vote_average.median()), 4),
    })


def main():
    df = common.load()

    y = df.groupby('year').apply(agg, include_groups=False).reset_index()
    y['n'] = y['n'].astype(int)
    y.to_csv(os.path.join(common.DATA, 'yearly.csv'), index=False, encoding='utf-8')
    print(f'yearly.csv          {len(y)} 行（{y.year.min()}–{y.year.max()}）')

    rows = []
    for name in common.GENRE.values():
        sub = df[common.has_genre(df, name)]
        if len(sub) < 100:
            continue
        t = sub.groupby('year').apply(agg, include_groups=False).reset_index()
        t.insert(0, 'genre', name)
        rows.append(t)
    byg = pd.concat(rows, ignore_index=True)
    byg.to_csv(os.path.join(common.DATA, 'yearly_by_genre.csv'), index=False, encoding='utf-8')
    print(f'yearly_by_genre.csv {len(byg)} 行（{byg.genre.nunique()} 个类型 × 年份）')

    print('\n抽样（全类型，每十年中间那年）：')
    print(y[y.year.isin([1965, 1985, 2005, 2020])].to_string(index=False))


if __name__ == '__main__':
    main()
