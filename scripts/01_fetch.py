#!/usr/bin/env python3
"""TMDB 全量采集：元数据（按年份分片）+ 海报分级下载。

【仅 A 使用】本脚本需要 API key（.env），数据已采集完成，队友不需要它。
复现或补数据时才重跑；结果直接读 data/ 下的 CSV。

为什么必须按年份分片：TMDB /discover 页数上限 500 页（page=501 直接 400）。
一个不加年份的查询最多只能拿到 500×20 = 1 万部，所以要按年切，每年单独翻页。

用法：
    # 1) 元数据全量（默认 1950-2025，票数 >= 100，约 3 万部，10-20 分钟）
    python3 scripts/01_fetch.py --metadata

    # 2) 海报分级下载（默认只下 1980 年后、票数 >= 200 的，w342）
    python3 scripts/01_fetch.py --posters

    # 3) 只要元数据，或只补海报
    python3 scripts/01_fetch.py --metadata --only
    python3 scripts/01_fetch.py --posters --min-votes 100 --size w500

断点续跑：元数据按年记进度，海报按文件是否存在跳过，中断了直接重跑同一条命令。
"""
import argparse, csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests

API = 'https://api.themoviedb.org/3'
IMG = 'https://image.tmdb.org/t/p/'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
POSTERS = os.path.join(DATA, 'posters')
META_CSV = os.path.join(DATA, 'movies.csv')
STATE = os.path.join(DATA, '_state.json')

FIELDS = ['id', 'title', 'original_title', 'original_language', 'release_date', 'year',
          'vote_count', 'vote_average', 'popularity', 'genre_ids', 'poster_path',
          'backdrop_path', 'adult', 'video', 'overview']


# ---------- 基础工具 ----------

def load_key():
    k = os.environ.get('TMDB_KEY', '').strip()
    if not k and os.path.exists(os.path.join(ROOT, '.env')):
        for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
            if line.strip().startswith('TMDB_KEY='):
                k = line.split('=', 1)[1].strip().strip('"\'')
    if not k:
        sys.exit('缺少 key：export TMDB_KEY=xxx，或在 大作业/.env 里写 TMDB_KEY=xxx')
    return k


KEY = None


def get(path, params=None, tries=5):
    """带重试的 GET。这台机器走代理，SSL 断连是常态，必须重试。"""
    params = dict(params or {})
    params['api_key'] = KEY
    for i in range(tries):
        try:
            r = requests.get(API + path, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:                 # 限流
                time.sleep(2 + i * 2)
                continue
            if r.status_code in (401, 404):
                raise RuntimeError(f'{r.status_code} {r.text[:120]}')
        except requests.RequestException:
            pass
        time.sleep(1.2 * (i + 1))
    raise RuntimeError(f'请求失败: {path} {params.get("page")}')


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {'meta_done_years': [], 'poster_fail': []}


def save_state(s):
    os.makedirs(DATA, exist_ok=True)
    json.dump(s, open(STATE, 'w'), ensure_ascii=False)


# ---------- 元数据 ----------

def year_total(y, min_votes):
    d = get('/discover/movie', {'page': 1, 'include_adult': 'false',
                                'language': 'zh-CN',
                                'vote_count.gte': min_votes,
                                'primary_release_date.gte': f'{y}-01-01',
                                'primary_release_date.lte': f'{y}-12-31'})
    return d.get('total_results', 0)


def crawl_year(y, min_votes, seen):
    """翻完某一年所有页，返回新增行。"""
    rows, page, total_pages = [], 1, 1
    while page <= min(total_pages, 500):
        d = get('/discover/movie', {'page': page, 'include_adult': 'false',
                                    'language': 'zh-CN', 'sort_by': 'vote_count.desc',
                                    'vote_count.gte': min_votes,
                                    'primary_release_date.gte': f'{y}-01-01',
                                    'primary_release_date.lte': f'{y}-12-31'})
        total_pages = d.get('total_pages', 1)
        results = d.get('results', [])
        if not results:
            break
        for m in results:
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


def do_metadata(args):
    os.makedirs(DATA, exist_ok=True)
    st = load_state()
    seen = set()
    if os.path.exists(META_CSV):                      # 续跑：先读已完成的
        for r in csv.DictReader(open(META_CSV, encoding='utf-8')):
            seen.add(int(r['id']))

    new_file = not os.path.exists(META_CSV)
    f = open(META_CSV, 'a', newline='', encoding='utf-8')
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    t0 = time.time()
    for y in range(args.start_year, args.end_year + 1):
        if y in st['meta_done_years']:
            continue
        n = year_total(y, args.min_votes)
        rows = crawl_year(y, args.min_votes, seen)
        w.writerows(rows)
        f.flush()
        st['meta_done_years'].append(y)
        save_state(st)
        print(f'{y}: 库内 {n:5d} 部 → 新增 {len(rows):5d}，累计 {len(seen):6d}，'
              f'{time.time()-t0:5.0f}s', flush=True)
    f.close()
    print(f'\n元数据完成：{len(seen)} 部 → {META_CSV}')


# ---------- 海报 ----------

def do_posters(args):
    os.makedirs(POSTERS, exist_ok=True)
    rows = [r for r in csv.DictReader(open(META_CSV, encoding='utf-8'))
            if r['poster_path'] and int(r['vote_count'] or 0) >= args.min_votes
            and r['year'] and args.start_year <= int(r['year']) <= args.end_year]
    todo = [(r['id'], r['poster_path']) for r in rows
            if not os.path.exists(os.path.join(POSTERS, f'{r["id"]}.jpg'))]
    print(f'命中 {len(rows)} 部，需要下载 {len(todo)} 张（已存在自动跳过）')

    url = IMG + args.size
    done = [0]
    t0 = time.time()

    def dl(item):
        tid, pp = item
        for i in range(4):
            try:
                r = requests.get(url + pp, timeout=30)
                if r.status_code == 200:
                    open(os.path.join(POSTERS, f'{tid}.jpg'), 'wb').write(r.content)
                    done[0] += 1
                    if done[0] % 200 == 0:
                        el = time.time() - t0
                        print(f'  {done[0]}/{len(todo)}  {el:.0f}s  预计剩余 '
                              f'{el/done[0]*(len(todo)-done[0])/60:.0f} 分钟', flush=True)
                    return None
            except requests.RequestException:
                pass
            time.sleep(0.8 * (i + 1))
        return tid

    with ThreadPoolExecutor(args.workers) as ex:
        fails = [x for x in ex.map(dl, todo) if x]
    print(f'完成：成功 {len(todo)-len(fails)}，失败 {len(fails)}，'
          f'耗时 {(time.time()-t0)/60:.1f} 分钟')
    if fails:
        print('失败 id（可重跑同一命令补齐）:', fails[:20])


def main():
    global KEY
    ap = argparse.ArgumentParser()
    ap.add_argument('--metadata', action='store_true')
    ap.add_argument('--posters', action='store_true')
    ap.add_argument('--start-year', type=int, default=1950)
    ap.add_argument('--end-year', type=int, default=2025)
    ap.add_argument('--min-votes', type=int, default=100)
    ap.add_argument('--size', default='w342', choices=['w342', 'w500', 'original'])
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()
    if not (args.metadata or args.posters):
        ap.error('至少指定 --metadata 或 --posters')
    KEY = load_key()
    if args.metadata:
        do_metadata(args)
    if args.posters:
        do_posters(args)


if __name__ == '__main__':
    main()
