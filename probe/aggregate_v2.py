#!/usr/bin/env python3
"""v2 年度聚合：口径与 scripts/04_yearly.py 一致，但写 outputs/a/，不动 data/。"""
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')

GENRE = {28: '动作', 12: '冒险', 16: '动画', 35: '喜剧', 80: '犯罪', 99: '纪录',
         18: '剧情', 10751: '家庭', 14: '奇幻', 36: '历史', 27: '恐怖', 10402: '音乐',
         9648: '悬疑', 10749: '爱情', 878: '科幻', 10770: '电视电影', 53: '惊悚',
         10752: '战争', 37: '西部'}


def load():
    m = pd.read_csv(os.path.join(DATA, 'movies.csv'), dtype={'id': int})
    exp = os.path.join(OUT, 'era_expansion.csv')
    if os.path.exists(exp):
        m = pd.concat([m, pd.read_csv(exp, dtype={'id': int})], ignore_index=True)
    f = pd.read_csv(os.path.join(OUT, 'color_features_v2.csv'))
    df = m.merge(f, left_on='id', right_on='tmdb_id')
    df['genres'] = df['genre_ids'].astype(str).apply(
        lambda s: [GENRE.get(int(g), g) for g in s.split('|') if g and g != 'nan'])
    return df


def agg(g):
    return pd.Series({
        'n': int(len(g)),
        'med_s': round(float(g.mean_s.median()), 4),
        'med_v': round(float(g.mean_v.median()), 4),
        'med_colorful': round(float(g.colorful.median()), 4),
        'med_vote': round(float(g.vote_average.median()), 4),
    })


def main():
    df = load()
    y = df.groupby('year').apply(agg, include_groups=False).reset_index()
    y['n'] = y['n'].astype(int)
    y.to_csv(os.path.join(OUT, 'yearly_v2.csv'), index=False, encoding='utf-8')
    print(f'yearly_v2.csv  {len(y)} 行（{y.year.min()}–{y.year.max()}）')

    rows = []
    for name in GENRE.values():
        sub = df[df.genres.apply(lambda gs: name in gs)]
        if len(sub) < 100:
            continue
        t = sub.groupby('year').apply(agg, include_groups=False).reset_index()
        t.insert(0, 'genre', name)
        rows.append(t)
    byg = pd.concat(rows, ignore_index=True)
    byg.to_csv(os.path.join(OUT, 'yearly_by_genre_v2.csv'), index=False, encoding='utf-8')
    print(f'yearly_by_genre_v2.csv {len(byg)} 行（{byg.genre.nunique()} 个类型 × 年份）')


if __name__ == '__main__':
    main()
