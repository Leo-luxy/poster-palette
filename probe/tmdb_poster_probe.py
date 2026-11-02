#!/usr/bin/env python3
"""
海报配色探针：验证「能不能拿到电影海报 + 能不能批量提主色」。

三条取图路线（按推荐顺序）：
  csv   —— 最省事。Kaggle "The Movies Dataset" 的 movies_metadata.csv 里已有
           poster_path（形如 /abc123.jpg），直接拼图床前缀即可，零爬虫零 key。
  api   —— 官方 API，需免费注册 v3 key（环境变量 TMDB_KEY）。
  scrape—— 不注册的兜底：抓 tmdb.org 电影页的 og:image。
           注意：curl 能过，requests/urllib 会被 Cloudflare 拦成 403，
           所以这里用 curl 子进程。

用法：
  python3 tmdb_poster_probe.py --demo                 # 内置 14 个片名跑一遍
  python3 tmdb_poster_probe.py --meta movies_metadata.csv --limit 500
  TMDB_KEY=xxx python3 tmdb_poster_probe.py --meta links.csv --source api

输出：cache/ 下存图（断点续跑会自动跳过），palettes.csv 存每张海报的 5 个主色及占比。
"""
import argparse, csv, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import numpy as np
import requests
from PIL import Image
from sklearn.cluster import KMeans

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}
IMG = 'https://image.tmdb.org/t/p/w500'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')

DEMO_IDS = [238, 11, 129, 680, 13, 155, 27205, 496243, 24428, 603, 550, 769, 122, 424]


def poster_path_from_tmdb_page(tmdb_id):
    """路线 scrape：curl 拿页面，正则取 og:image。实测可用，但 Cloudflare 会变脸。"""
    url = f'https://www.themoviedb.org/movie/{tmdb_id}'
    html = subprocess.run(['curl', '-sL', '-m', '20', '-A', UA['User-Agent'], url],
                          capture_output=True, text=True).stdout
    m = re.search(r'og:image" content="https://[^"]+/t/p/w500/([^"]+\.jpg)"', html)
    return m.group(1) if m else None


def poster_path_from_api(tmdb_id, key):
    r = requests.get(f'https://api.themoviedb.org/3/movie/{tmdb_id}',
                     params={'api_key': key}, timeout=20)
    return r.json().get('poster_path', '').lstrip('/') or None


def palette(path, k=5, crop_bottom=0.12):
    """裁掉底部角标/文字区，缩图后 K-Means。返回 [(r,g,b,share), ...]。"""
    img = Image.open(path).convert('RGB')
    w, h = img.size
    img = img.crop((0, 0, w, int(h * (1 - crop_bottom)))).resize((100, 130))
    X = np.asarray(img).reshape(-1, 3).astype(np.float64)
    km = KMeans(n_clusters=k, n_init=4, random_state=0).fit(X)
    share = np.bincount(km.labels_) / len(X)
    order = share.argsort()[::-1]
    return [(*(km.cluster_centers_[i].round().astype(int)), round(share[i], 3)) for i in order]


def fetch_one(task):
    tmdb_id, ppath = task
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, f'{tmdb_id}.jpg')
    if not os.path.exists(dst):
        r = requests.get(IMG + '/' + ppath, headers=UA, timeout=30)
        if r.status_code != 200:
            return tmdb_id, None, f'HTTP {r.status_code}'
        open(dst, 'wb').write(r.content)
    return tmdb_id, dst, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--meta', help='含 tmdb_id 列的 csv（Kaggle movies_metadata.csv 或 MovieLens links.csv）')
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--source', choices=['scrape', 'api'], default='scrape')
    ap.add_argument('--out', default='palettes.csv')
    a = ap.parse_args()

    # 1) 拿到「tmdb_id -> poster_path」
    tasks = []
    if a.demo:
        ids = DEMO_IDS
        get = poster_path_from_tmdb_page
    else:
        rows = list(csv.DictReader(open(a.meta, encoding='utf-8', errors='ignore')))[:a.limit]
        ids = [int(float(r.get('tmdbId') or r.get('id'))) for r in rows]
        if 'poster_path' in rows[0]:                       # 路线 csv：白嫖现成 poster_path
            tasks = [(int(float(r['id'])), r['poster_path'].lstrip('/'))
                     for r in rows if r.get('poster_path')]
            get = None
        else:
            get = (lambda i: poster_path_from_api(i, os.environ['TMDB_KEY'])) \
                if a.source == 'api' else poster_path_from_tmdb_page

    t0 = time.time()
    if get:
        with ThreadPoolExecutor(8) as ex:
            paths = list(ex.map(get, ids))
        tasks = [(i, p) for i, p in zip(ids, paths) if p]
        print(f'解析到 {len(tasks)}/{len(ids)} 张海报，{time.time()-t0:.1f}s')

    # 2) 下载（带缓存）
    t1 = time.time()
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(fetch_one, tasks))
    ok = [(i, p) for i, p, err in got if p]
    print(f'下载 {len(ok)}/{len(tasks)} 张，{time.time()-t1:.1f}s → {CACHE}')

    # 3) 提主色
    t2 = time.time()
    with ThreadPoolExecutor(8) as ex:
        pals = list(ex.map(lambda t: (t[0], palette(t[1])), ok))
    print(f'K-Means 提色 {len(pals)} 张，{time.time()-t2:.1f}s')

    with open(a.out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['tmdb_id'] + [f'c{i+1}' for i in range(5)] + [f's{i+1}' for i in range(5)])
        for tid, pal in pals:
            w.writerow([tid] + [f'#{r:02x}{g:02x}{b:02x}' for r, g, b, _ in pal]
                       + [s for *_, s in pal])
    print(f'→ {a.out}')


if __name__ == '__main__':
    sys.exit(main())
