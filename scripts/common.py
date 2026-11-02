#!/usr/bin/env python3
"""全组共用的读数据、类型表、配色。B/C/D 都从这里 import，保证口径一致。"""
import os

os.environ.setdefault('MPLCONFIGDIR', '/tmp/mpl')   # 避免 matplotlib 字体缓存报错

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
FIG = os.path.join(ROOT, 'figures')

GENRE = {28: '动作', 12: '冒险', 16: '动画', 35: '喜剧', 80: '犯罪', 99: '纪录',
         18: '剧情', 10751: '家庭', 14: '奇幻', 36: '历史', 27: '恐怖', 10402: '音乐',
         9648: '悬疑', 10749: '爱情', 878: '科幻', 10770: '电视电影', 53: '惊悚',
         10752: '战争', 37: '西部'}
GID = {v: k for k, v in GENRE.items()}

# 统一配色：主讲三类用饱和色，对照类用灰调
COLOR = {'科幻': '#2b6cb0', '爱情': '#dd6b20', '恐怖': '#2f855a',
         '动作': '#c53030', '喜剧': '#b7791f', '剧情': '#4a5568',
         '犯罪': '#553c9a', '惊悚': '#2c7a7b', '悬疑': '#975a16'}

# 每格样本量不足这个数就不画
MIN_CELL = 30


def load():
    """读两张表并合并，加 year/decade/genre 列表。"""
    m = pd.read_csv(os.path.join(DATA, 'movies.csv'), dtype={'id': int})
    f = pd.read_csv(os.path.join(DATA, 'color_features.csv'))
    df = m.merge(f, left_on='id', right_on='tmdb_id')
    df['decade'] = (df['year'] // 10 * 10).astype(int)
    df['genres'] = df['genre_ids'].astype(str).apply(
        lambda s: [GENRE.get(int(g), g) for g in s.split('|') if g and g != 'nan'])
    return df


def has_genre(df, name):
    return df['genres'].apply(lambda gs: name in gs)


def usable_hue(df):
    """色相统计只在这些行上做：排除近乎纯灰的海报。"""
    return df[df['sat_frac'] >= 0.10]


def hue_share(df, name):
    """某个类型的 12 扇区色相占比（已归一）。"""
    sub = usable_hue(df[has_genre(df, name)])
    cols = [f'h{i}' for i in range(12)]
    s = sub[cols].sum(0)
    return s / s.sum()
