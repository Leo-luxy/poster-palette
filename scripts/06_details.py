#!/usr/bin/env python3
"""补详情字段：逐片调 /movie/{id}，补生产国家、预算、票房、片长等。

为什么单独一个文件：movies.csv 是用 /discover 批量拿的，里面没有
production_countries、budget、revenue——这些只在单片详情接口里。

产物 data/movie_details.csv，和 movies.csv 用 id 关联；common.load() 会自动左连接。

断点续跑：已完成的 id 会跳过，中断后重跑同一条命令即可。
"""
import csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(DATA, 'movie_details.csv')
API = 'https://api.themoviedb.org/3'

FIELDS = ['id', 'production_countries', 'country_names', 'production_companies',
          'budget', 'revenue', 'runtime', 'status', 'spoken_languages',
          'collection_name', 'imdb_id']


def load_key():
    k = os.environ.get('TMDB_KEY', '').strip()
    if not k and os.path.exists(os.path.join(ROOT, '.env')):
        for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
            if line.strip().startswith('TMDB_KEY='):
                k = line.split('=', 1)[1].strip().strip('"\'')
    if not k:
        sys.exit('缺少 key：export TMDB_KEY=xxx，或在大作业/.env 里写 TMDB_KEY=xxx')
    return k


KEY = None


def fetch(mid):
    for i in range(4):
        try:
            r = requests.get(f'{API}/movie/{mid}',
                             params={'api_key': KEY, 'language': 'zh-CN'}, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(2 + 2 * i)
                continue
        except requests.RequestException:
            pass
        time.sleep(1.0 * (i + 1))
    return None


def row_of(mid, d):
    if not d:
        return {'id': mid, 'production_countries': '', 'country_names': '',
                'production_companies': '', 'budget': '', 'revenue': '',
                'runtime': '', 'status': 'MISSING', 'spoken_languages': '',
                'collection_name': '', 'imdb_id': ''}
    countries = d.get('production_countries') or []
    return {
        'id': mid,
        'production_countries': '|'.join(c.get('iso_3166_1', '') for c in countries),
        'country_names': '|'.join(c.get('name', '') for c in countries),
        'production_companies': '|'.join(c.get('name', '') for c in (d.get('production_companies') or [])[:3]),
        'budget': d.get('budget') or 0,
        'revenue': d.get('revenue') or 0,
        'runtime': d.get('runtime') or '',
        'status': d.get('status', ''),
        'spoken_languages': '|'.join(l.get('iso_639_1', '') for l in (d.get('spoken_languages') or [])),
        'collection_name': (d.get('belongs_to_collection') or {}).get('name', ''),
        'imdb_id': d.get('imdb_id') or '',
    }


def main():
    global KEY
    KEY = load_key()

    ids = [int(r['id']) for r in csv.DictReader(open(os.path.join(DATA, 'movies.csv'), encoding='utf-8'))]

    # 单实例锁：两个进程同时写同一个 csv 会产生重复行（踩过一次）
    try:
        import fcntl
        lock = open(os.path.join(DATA, '.details.lock'), 'w')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            sys.exit('已经有一个 06_details.py 在跑，先别开第二个')
    except ImportError:
        lock = None  # Windows 没有 fcntl，跳过

    done = set()
    if os.path.exists(OUT):
        done = {int(r['id']) for r in csv.DictReader(open(OUT, encoding='utf-8'))}
    todo = [i for i in ids if i not in done]
    print(f'总计 {len(ids)}，已完成 {len(done)}，待补 {len(todo)}', flush=True)
    if not todo:
        print('没有要补的')
        return

    new_file = not os.path.exists(OUT)
    f = open(OUT, 'a', newline='', encoding='utf-8')
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()

    t0, n, miss = time.time(), 0, 0
    with ThreadPoolExecutor(10) as ex:
        for mid, d in zip(todo, ex.map(fetch, todo, chunksize=8)):
            row = row_of(mid, d)
            if row['status'] == 'MISSING':
                miss += 1
            w.writerow(row)
            n += 1
            if n % 500 == 0:
                f.flush()
                el = time.time() - t0
                print(f'  {n}/{len(todo)}  {el/60:.1f} min  剩余约 {el/n*(len(todo)-n)/60:.0f} min',
                      flush=True)
    f.close()
    print(f'\n完成 {n} 条，其中详情缺失 {miss} 条，耗时 {(time.time()-t0)/60:.1f} 分钟')
    print(f'→ {OUT}')


if __name__ == '__main__':
    main()
