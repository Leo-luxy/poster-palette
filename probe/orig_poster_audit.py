#!/usr/bin/env python3
"""诊断：现有海报里有多少是中文版，能不能换成「原版」。

分三步，可以只跑前一步：
  --sample N     按 年代×国家 分层抽 N 部，查每部的海报语言清单（每部 1 次 API）
  --compare      对抽样里已经下好的原版候选，算配色特征和现有的差多少
  --full         全量 14,662 部查语言清单，产出 outputs/a/poster_plan.csv（约 30 分钟）

不解压、不改 data/：所有产物写 outputs/a/。
"""
import argparse, csv, json, os, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')
CACHE = os.path.join(ROOT, 'probe', 'cache')
API = 'https://api.themoviedb.org/3'
IMG = 'https://image.tmdb.org/t/p/w342'


def load_key():
    k = os.environ.get('TMDB_KEY', '').strip()
    if not k:
        p = os.path.join(ROOT, '.env')
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                if line.strip().startswith('TMDB_KEY='):
                    k = line.split('=', 1)[1].strip().strip('"\'')
    if not k:
        sys.exit('缺少 TMDB_KEY')
    return k


KEY = load_key()


def get(path, params=None, tries=5):
    params = dict(params or {})
    params['api_key'] = KEY
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


def load_movies():
    return {r['id']: r for r in csv.DictReader(open(os.path.join(DATA, 'movies.csv'), encoding='utf-8'))}


def load_countries():
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'movie_details.csv'), encoding='utf-8')):
        out[r['id']] = [c.strip() for c in r['production_countries'].split('|') if c.strip()]
    return out


def poster_langs(mid, orig_lang):
    """查一部片的全部海报语言标签。include_image_language 最多给几个语言 + null。"""
    langs = {orig_lang, 'en', 'zh', 'null'}
    langs.discard('')
    d = get(f'/movie/{mid}/images', {'include_image_language': ','.join(sorted(langs))})
    if not d:
        return None
    ps = d.get('posters') or []
    return [{'lang': p.get('iso_639_1'), 'path': p['file_path'],
             'vote': p.get('vote_average') or 0, 'w': p.get('width') or 0,
             'h': p.get('height') or 0} for p in ps]


def pick(entries, cur_path, orig_lang):
    """返回 (目标, 选中的条目)。目标 ∈ orig / textless / en / keep。

    现有那张本来就是原语言或无文字 → keep，不做无谓替换（同语言换一张只是换噪声）。
    """
    if not entries:
        return 'keep', None
    cur = next((e for e in entries if e['path'] == cur_path), None)
    if cur is not None and cur['lang'] in (orig_lang, None):
        return 'keep', None
    # 现有那张自己就带了标签，先排除它，免得原地打转
    others = [e for e in entries if e['path'] != cur_path]
    zh = [e for e in others if e['lang'] == 'zh']
    for tag, want in (('orig', orig_lang), ('textless', None), ('en', 'en')):
        cand = [e for e in others if e['lang'] == want]
        if cand:
            cand.sort(key=lambda e: (e['vote'], e['w']), reverse=True)
            return tag, cand[0]
    return 'keep', None


def stratified_sample(movies, countries, n, seed=0):
    """年代 × 国家 分层：每格先取 1 部，再按剩余量补。"""
    import random
    rng = random.Random(seed)
    cells = defaultdict(list)
    for mid, m in movies.items():
        if not m['poster_path'] or not m['year']:
            continue
        dec = int(m['year']) // 10 * 10
        cs = countries.get(mid) or []
        # 只认头部国家，格子不碎
        c = next((x for x in ('US', 'GB', 'FR', 'IT', 'DE', 'JP', 'CN', 'IN', 'KR', 'ES') if x in cs), 'other')
        cells[(dec, c)].append(mid)
    for v in cells.values():
        rng.shuffle(v)
    out, i = [], 0
    while len(out) < n:
        added = False
        for k in sorted(cells):
            if i < len(cells[k]) and len(out) < n:
                out.append(cells[k][i])
                added = True
        if not added:
            break
        i += 1
    return out, {k: len(v) for k, v in cells.items()}


def do_sample(args):
    os.makedirs(CACHE, exist_ok=True)
    movies = load_movies()
    countries = load_countries()
    ids, sizes = stratified_sample(movies, countries, args.sample)
    print(f'分 {len(sizes)} 格，抽 {len(ids)} 部')
    t0 = time.time()
    rows = []

    def work(mid):
        m = movies[mid]
        ents = poster_langs(mid, m['original_language'])
        if ents is None:
            return {'id': mid, 'err': 1}
        tag, e = pick(ents, m['poster_path'], m['original_language'])
        cnt = Counter(str(x['lang']) for x in ents)
        return {'id': mid, 'title': m['title'], 'year': m['year'],
                'country': '|'.join(countries.get(mid, [])), 'orig_lang': m['original_language'],
                'n_posters': len(ents), 'n_zh': cnt['zh'], 'n_orig': cnt[m['original_language']],
                'n_textless': cnt['None'], 'n_en': cnt['en'],
                'pick': tag, 'pick_path': e['path'] if e else '',
                'pick_vote': e['vote'] if e else '', 'pick_w': e['w'] if e else '',
                'cur_lang': next((str(x['lang']) for x in ents if x['path'] == m['poster_path']), '?'),
                'cur_path': m['poster_path']}

    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(work, ids):
            rows.append(r)
    ok = [r for r in rows if not r.get('err')]
    print(f'{len(ok)} 部拿到清单，{time.time()-t0:.0f}s')
    print('现有海报的语言分布:', Counter(r['cur_lang'] for r in ok))
    print('可替换成:', Counter(r['pick'] for r in ok))
    p = os.path.join(OUT, 'poster_sample.csv')
    os.makedirs(OUT, exist_ok=True)
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ok[0].keys()))
        w.writeheader()
        w.writerows(ok)
    print('→', p)
    # 交叉：年代 × 现有语言
    tab = defaultdict(Counter)
    for r in ok:
        tab[int(r['year']) // 10 * 10][r['cur_lang']] += 1
    print('\n年代   总数  zh   非zh')
    for dec in sorted(tab):
        c = tab[dec]
        t = sum(c.values())
        print(f'{dec}s  {t:4d}  {c["zh"]:4d}  {t-c["zh"]:4d}')


def do_full(args):
    movies = load_movies()
    ids = [mid for mid, m in movies.items() if m['poster_path']]
    print(f'全量 {len(ids)} 部，预计 {len(ids)/8*0.25/60:.0f} 分钟')

    def work(mid):
        m = movies[mid]
        ents = poster_langs(mid, m['original_language'])
        if ents is None:
            return {'id': mid, 'err': 1}
        tag, e = pick(ents, m['poster_path'], m['original_language'])
        return {'id': mid, 'year': m['year'], 'orig_lang': m['original_language'],
                'cur_path': m['poster_path'],
                'cur_lang': next((str(x['lang']) for x in ents if x['path'] == m['poster_path']), '?'),
                'pick': tag, 'pick_path': e['path'] if e else '', 'pick_lang': str(e['lang']) if e else ''}

    rows, done, t0 = [], 0, time.time()
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(work, ids):
            rows.append(r)
            done += 1
            if done % 1000 == 0:
                print(f'  {done}/{len(ids)}  {(time.time()-t0)/60:.1f} 分钟', flush=True)
    ok = [r for r in rows if not r.get('err')]
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, 'poster_plan.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ok[0].keys()))
        w.writeheader()
        w.writerows(ok)
    print('→', p)
    print('现有:', Counter(r['cur_lang'] for r in ok))
    print('替换:', Counter(r['pick'] for r in ok))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=400)
    ap.add_argument('--full', action='store_true')
    a = ap.parse_args()
    do_full(a) if a.full else do_sample(a)
