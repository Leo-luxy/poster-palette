#!/usr/bin/env python3
"""回滚：把 data/posters/ 恢复成覆盖前的样子。

依据是 data/movies.csv 里记的 poster_path —— 每部片当初下载的那张图的原始路径。
覆盖前请先另存一份 movies.csv（覆盖不会改它，但保险）。

用法：
    python3 probe/restore_v1_posters.py            # 全部恢复
    python3 probe/restore_v1_posters.py --limit 100  # 先试 100 张
"""
import argparse, csv, os, time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
POSTERS = os.path.join(DATA, 'posters')
IMG = 'https://image.tmdb.org/t/p/w342'


def dl(item):
    mid, path = item
    for i in range(4):
        try:
            r = requests.get(IMG + path, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                open(os.path.join(POSTERS, f'{mid}.jpg'), 'wb').write(r.content)
                return mid, None
        except requests.RequestException:
            pass
        time.sleep(0.8 * (i + 1))
    return mid, 'fail'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    rows = [(r['id'], r['poster_path']) for r in
            csv.DictReader(open(os.path.join(DATA, 'movies.csv'), encoding='utf-8'))
            if r['poster_path']]
    if a.limit:
        rows = rows[:a.limit]
    print(f'恢复 {len(rows)} 张（原始路径来自 movies.csv）')
    t0, n = time.time(), 0
    with ThreadPoolExecutor(8) as ex:
        for mid, err in ex.map(dl, rows):
            n += 1
            if n % 500 == 0:
                print(f'  {n}/{len(rows)}  {(time.time()-t0)/60:.1f} 分钟', flush=True)
    print('完成')


if __name__ == '__main__':
    main()
