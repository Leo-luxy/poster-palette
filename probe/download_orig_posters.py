#!/usr/bin/env python3
"""按 poster_plan_v2.csv 下载海报到 outputs/a/posters_v2/。

- action 为 use_* 的：下 pick_path
- source 为 new 的：无条件下（本地本来就没有）
- 其余 keep：本地复用 data/posters 里的原文件，不下载

可断点续跑：文件存在且大于 1KB 就跳过。
"""
import csv, os, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs', 'a')
PLAN = os.path.join(OUT, 'poster_plan_v2.csv')
DST = os.path.join(OUT, 'posters_v2')
IMG = 'https://image.tmdb.org/t/p/w342'


def dl(item):
    mid, path = item
    dst = os.path.join(DST, f'{mid}.jpg')
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return mid, None
    for i in range(4):
        try:
            r = requests.get(IMG + path, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                open(dst, 'wb').write(r.content)
                return mid, None
            if r.status_code == 404:
                return mid, '404'
        except requests.RequestException:
            pass
        time.sleep(0.8 * (i + 1))
    return mid, 'fail'


def main():
    os.makedirs(DST, exist_ok=True)
    rows = list(csv.DictReader(open(PLAN, encoding='utf-8')))
    todo = [(r['id'], r['pick_path']) for r in rows
            if r['pick_path'] and (r['source'] == 'new' or r['action'].startswith('use_'))]
    print('计划', len(rows), '部；需下载', len(todo), '张')
    print('动作分布:', Counter(r['action'] for r in rows))
    t0, n = time.time(), 0
    bad = []
    with ThreadPoolExecutor(int(os.environ.get('WORKERS', 8))) as ex:
        for mid, err in ex.map(dl, todo):
            n += 1
            if err:
                bad.append((mid, err))
            if n % 500 == 0:
                el = time.time() - t0
                print(f'  {n}/{len(todo)}  {el/60:.1f} 分钟  剩余 ~{el/n*(len(todo)-n)/60:.0f} 分钟',
                      flush=True)
    print(f'完成 {n}，失败 {len(bad)}')
    if bad:
        print('失败示例:', bad[:10])


if __name__ == '__main__':
    main()
