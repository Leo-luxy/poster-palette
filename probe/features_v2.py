#!/usr/bin/env python3
"""v2 特征：优先用 outputs/a/posters_v2/，没有再回落到 data/posters/。

输出 outputs/a/color_features_v2.csv，字段与 data/color_features.csv 完全一致，
可以直接替换或对比。
"""
import csv, importlib.util, os
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')
V2 = os.path.join(OUT, 'posters_v2')

spec = importlib.util.spec_from_file_location('f3', os.path.join(ROOT, 'scripts', '03_features.py'))
f3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f3)

FIELDS = f3.FIELDS


def path_for(tid):
    p = os.path.join(V2, f'{tid}.jpg')
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        return p
    p = os.path.join(DATA, 'posters', f'{tid}.jpg')
    return p if os.path.exists(p) else None


def work(tid):
    p = path_for(tid)
    if not p:
        return tid, None
    try:
        return tid, f3.features(p)
    except Exception as e:
        return tid, {'error': str(e)[:60]}


def main():
    ids = []
    for r in csv.DictReader(open(os.path.join(DATA, 'movies.csv'), encoding='utf-8')):
        if r['poster_path']:
            ids.append(int(r['id']))
    p2 = os.path.join(OUT, 'era_expansion.csv')
    if os.path.exists(p2):
        for r in csv.DictReader(open(p2, encoding='utf-8')):
            if r['poster_path']:
                ids.append(int(r['id']))
    ids = sorted(set(ids))
    print(f'待算 {len(ids)} 部', flush=True)

    rows, err, n = [], 0, 0
    with ProcessPoolExecutor(max_workers=6) as ex:
        for tid, feat in ex.map(work, ids, chunksize=64):
            n += 1
            if feat is None or (isinstance(feat, dict) and 'error' in feat):
                err += 1
                continue
            feat['tmdb_id'] = tid
            rows.append(feat)
            if n % 2000 == 0:
                print(f'  {n}/{len(ids)}', flush=True)

    p = os.path.join(OUT, 'color_features_v2.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, '') for k in FIELDS} for r in rows)
    print(f'完成 {len(rows)} 行，失败/无图 {err} → {p}')


if __name__ == '__main__':
    main()
