#!/usr/bin/env python3
"""为全部电影挑「原语言海报」。

优先级：iso_639_1 == original_language → null（无文字）→ en → 保持现状。
现有海报已经是原语言/无文字的，直接 keep，不重下。

输入：data/movies.csv + outputs/a/era_expansion.csv
产物：outputs/a/poster_plan_v2.csv（每部一行：现状/选择/动作）
可断点续跑：已写入的 id 会跳过。
"""
import csv, json, os, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')
PLAN = os.path.join(OUT, 'poster_plan_v2.csv')
API = 'https://api.themoviedb.org/3'
FIELDS = ['id', 'source', 'year', 'orig_lang', 'cur_path', 'cur_lang',
          'n_posters', 'action', 'pick_path', 'pick_lang']


def load_key():
    k = os.environ.get('TMDB_KEY', '').strip()
    if not k:
        for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
            if line.strip().startswith('TMDB_KEY='):
                k = line.split('=', 1)[1].strip().strip('"\'')
    return k


KEY = load_key()


SESSION = requests.Session()
FAILS = [0]          # 连续失败计数，用来判断网络是不是断了
LOCK = __import__('threading').Lock()


def get(path, params, tries=6):
    """这台机器走代理，SSL 断连是常态：短超时 + 多次重试 + 失败计数。"""
    params = dict(params, api_key=KEY)
    for i in range(tries):
        try:
            r = SESSION.get(API + path, params=params, timeout=12)
            if r.status_code == 200:
                with LOCK:
                    FAILS[0] = 0
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(2 + 2 * i)
                continue
        except requests.RequestException:
            pass
        with LOCK:
            FAILS[0] += 1
            n = FAILS[0]
        # 连续失败 30 次 = 网络断了，全体歇 20 秒再试
        if n > 0 and n % 30 == 0:
            time.sleep(20)
        else:
            time.sleep(0.5 * (i + 1))
    return None


def pick(entries, cur_path, orig):
    """返回 (action, path, lang)。"""
    cur = next((e for e in entries if e['file_path'] == cur_path), None)
    cur_lang = str(cur['iso_639_1']) if cur else '?'
    if cur and (cur['iso_639_1'] == orig or cur['iso_639_1'] is None):
        return 'keep', cur_path, cur_lang
    for tag, lang in (('use_orig', orig), ('use_textless', None), ('use_en', 'en')):
        c = [e for e in entries if e['iso_639_1'] == lang and e['file_path'] != cur_path]
        if c:
            c.sort(key=lambda e: (e['vote_average'] or 0, e['width'] or 0), reverse=True)
            return tag, c[0]['file_path'], str(lang)
    return 'keep', cur_path, cur_lang


def main():
    films = []
    for r in csv.DictReader(open(os.path.join(DATA, 'movies.csv'), encoding='utf-8')):
        films.append({'id': r['id'], 'source': 'old', 'year': r['year'],
                      'orig_lang': r['original_language'], 'cur_path': r['poster_path']})
    p2 = os.path.join(OUT, 'era_expansion.csv')
    if os.path.exists(p2):
        for r in csv.DictReader(open(p2, encoding='utf-8')):
            films.append({'id': r['id'], 'source': 'new', 'year': r['year'],
                          'orig_lang': r['original_language'], 'cur_path': r['poster_path']})
    films = [f for f in films if f['cur_path']]
    print(f'待查 {len(films)} 部', flush=True)

    done = set()
    if os.path.exists(PLAN):
        done = {r['id'] for r in csv.DictReader(open(PLAN, encoding='utf-8'))}
        print(f'断点续跑：已完成 {len(done)}', flush=True)
    todo = [f for f in films if f['id'] not in done]
    print(f'还需查 {len(todo)} 部', flush=True)

    f = open(PLAN, 'a', newline='', encoding='utf-8')
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if not done:
        w.writeheader()
    t0, n = time.time(), 0

    def work(m):
        langs = {m['orig_lang'], 'en', 'zh', 'null'}
        langs.discard('')
        d = get(f'/movie/{m["id"]}/images',
                {'include_image_language': ','.join(sorted(langs))})
        if not d:
            return None                      # 失败不落盘，下次重跑会再试
        ents = d.get('posters') or []
        act, path, lang = pick(ents, m['cur_path'], m['orig_lang'])
        return {'id': m['id'], 'source': m['source'], 'year': m['year'],
                'orig_lang': m['orig_lang'], 'cur_path': m['cur_path'],
                'cur_lang': lang if act == 'keep' else next(
                    (str(e['iso_639_1']) for e in ents if e['file_path'] == m['cur_path']), '?'),
                'n_posters': len(ents), 'action': act, 'pick_path': path, 'pick_lang': lang}

    with ThreadPoolExecutor(int(os.environ.get('WORKERS', 4))) as ex:
        for row in ex.map(work, todo):
            if not row:
                continue
            w.writerow(row)
            n += 1
            if n % 200 == 0:
                el = time.time() - t0
                print(f'  {n}/{len(todo)}  {el/60:.1f} 分钟  剩余 ~{el/n*(len(todo)-n)/60:.0f} 分钟',
                      flush=True)
                f.flush()
    f.close()
    print(f'完成 {n} 部 → {PLAN}')


if __name__ == '__main__':
    main()
