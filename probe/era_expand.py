#!/usr/bin/env python3
"""按「每年票数前 2.6%」补老片：只拉现有 movies.csv 里没有的片子。

门槛来自 outputs/a/era_cutoff.csv（逐年算的 2.6% 名次对应票数）。
产物 outputs/a/era_expansion.csv，字段与 movies.csv 一致，可直接 concat。
不下图、不改 data/。

用法：
    python3 probe/era_expand.py            # 全量抓取
    python3 probe/era_expand.py --years 1950-1979
"""
import argparse, csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')
API = 'https://api.themoviedb.org/3'
FIELDS = ['id', 'title', 'original_title', 'original_language', 'release_date', 'year',
          'vote_count', 'vote_average', 'popularity', 'genre_ids', 'poster_path',
          'backdrop_path', 'adult', 'video', 'overview']


def load_key():
    k = os.environ.get('TMDB_KEY', '').strip()
    if not k:
        for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
            if line.strip().startswith('TMDB_KEY='):
                k = line.split('=', 1)[1].strip().strip('"\'')
    if not k:
        sys.exit('缺少 TMDB_KEY')
    return k


KEY = load_key()


def get(path, params, tries=5):
    params = dict(params, api_key=KEY)
    for i in range(tries):
        try:
            r = requests.get(API + path, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + 2 * i)
                continue
            if r.status_code in (401, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.2 * (i + 1))
    return None


def crawl_year(y, cutoff, seen):
    """翻完一年，返回新增行。已存在的 id 跳过。"""
    rows, page, total_pages = [], 1, 1
    while page <= min(total_pages, 500):
        d = get('/discover/movie', {
            'page': page, 'include_adult': 'false', 'language': 'zh-CN',
            'sort_by': 'vote_count.desc', 'vote_count.gte': cutoff,
            'primary_release_date.gte': f'{y}-01-01',
            'primary_release_date.lte': f'{y}-12-31'})
        if not d:
            break
        total_pages = d.get('total_pages', 1)
        res = d.get('results', [])
        if not res:
            break
        for m in res:
            if m['id'] in seen:
                continue
            seen.add(m['id'])
            rows.append({
                'id': m['id'], 'title': m.get('title', ''),
                'original_title': m.get('original_title', ''),
                'original_language': m.get('original_language', ''),
                'release_date': m.get('release_date', '') or '',
                'year': (m.get('release_date') or '')[:4],
                'vote_count': m.get('vote_count', 0),
                'vote_average': m.get('vote_average', 0),
                'popularity': m.get('popularity', 0),
                'genre_ids': '|'.join(str(g) for g in m.get('genre_ids', [])),
                'poster_path': m.get('poster_path') or '',
                'backdrop_path': m.get('backdrop_path') or '',
                'adult': m.get('adult', False), 'video': m.get('video', False),
                'overview': (m.get('overview') or '').replace('\n', ' ').strip(),
            })
        page += 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', default='1950-2025')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.years.split('-'))

    cut = {int(r['year']): int(r['cutoff'])
           for r in csv.DictReader(open(os.path.join(OUT, 'era_cutoff.csv'), encoding='utf-8'))}
    seen = {int(r['id']) for r in csv.DictReader(open(os.path.join(DATA, 'movies.csv'), encoding='utf-8'))}
    base = len(seen)
    years = [y for y in range(lo, hi + 1) if y in cut]

    t0 = time.time()
    done = [0]

    def work(y):
        rows = crawl_year(y, cut[y], seen)
        done[0] += 1
        print(f'  {done[0]}/{len(years)}  {y}  +{len(rows):4d}  累计新增 {len(seen)-base:5d}  '
              f'{time.time()-t0:5.0f}s', flush=True)
        return rows

    all_rows = []
    with ThreadPoolExecutor(a.workers) as ex:
        for rows in ex.map(work, years):
            all_rows.extend(rows)

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, 'era_expansion.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    print(f'\n新增 {len(all_rows)} 部 → {p}')
    print(f'其中无海报 {sum(1 for r in all_rows if not r["poster_path"])} 部')
    from collections import Counter
    c = Counter(int(r['year']) // 10 * 10 for r in all_rows if r['year'])
    print('年代分布:', dict(sorted(c.items())))
    print(f'总耗时 {(time.time()-t0)/60:.1f} 分钟')


if __name__ == '__main__':
    main()
