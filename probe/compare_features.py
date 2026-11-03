#!/usr/bin/env python3
"""第二步：把「现有海报」和「候选原版海报」都算一遍配色特征，看差多少。

只读 data/posters 里已有的图，候选图下载到 probe/cache/cand/。
产物：outputs/a/feature_delta.csv
"""
import csv, importlib.util, os, sys
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')
CAND = os.path.join(ROOT, 'probe', 'cache', 'cand')
IMG = 'https://image.tmdb.org/t/p/w342'

spec = importlib.util.spec_from_file_location('f3', os.path.join(ROOT, 'scripts', '03_features.py'))
f3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f3)

NUM = ['mean_s', 'mean_v', 'v_std', 'sat_frac', 'colorful'] + [f'h{i}' for i in range(12)] + ['ds1']


def dl(item):
    tid, path = item
    dst = os.path.join(CAND, f'{tid}.jpg')
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return tid, None
    for _ in range(3):
        try:
            r = requests.get(IMG + path, timeout=30)
            if r.status_code == 200:
                open(dst, 'wb').write(r.content)
                return tid, None
        except requests.RequestException:
            pass
    return tid, 'dl fail'


def main():
    os.makedirs(CAND, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(OUT, 'poster_sample.csv'), encoding='utf-8')))
    zh = [r for r in rows if r['cur_lang'] == 'zh' and r['orig_lang'] != 'zh' and r['pick_path']]
    ctrl = [r for r in rows if r['cur_lang'] == r['orig_lang'] and r['pick_path'] and r['pick'] != 'keep'][:80]
    todo = [(r['id'], r['pick_path']) for r in zh + ctrl]
    print(f'候选图 {len(todo)} 张（zh {len(zh)} + 对照 {len(ctrl)}）')
    with ThreadPoolExecutor(8) as ex:
        bad = [x for x in ex.map(dl, todo) if x[1]]
    print('下载失败', len(bad))

    out = []

    def work(r):
        tid = r['id']
        cur = os.path.join(DATA, 'posters', f'{tid}.jpg')
        cand = os.path.join(CAND, f'{tid}.jpg')
        if not (os.path.exists(cur) and os.path.exists(cand)):
            return None
        a, b = f3.features(cur), f3.features(cand)
        d = {'id': tid, 'year': r['year'], 'country': r['country'], 'orig_lang': r['orig_lang'],
             'cur_lang': r['cur_lang'], 'pick': r['pick'],
             'group': 'zh' if r in zh else 'ctrl'}
        for k in NUM:
            d[k] = round((b[k] or 0) - (a[k] or 0), 4)
        d['cur_mean_v'] = a['mean_v']
        d['cand_mean_v'] = b['mean_v']
        d['cur_colorful'] = a['colorful']
        d['cand_colorful'] = b['colorful']
        return d

    with ThreadPoolExecutor(6) as ex:
        for d in ex.map(work, zh + ctrl):
            if d:
                out.append(d)
    p = os.path.join(OUT, 'feature_delta.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f'{len(out)} 对特征 → {p}')


if __name__ == '__main__':
    main()
