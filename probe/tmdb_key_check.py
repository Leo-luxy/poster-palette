#!/usr/bin/env python3
"""拿到 key 之后的第一件事：验证 + 看返回里有什么。

用法：
    python3 tmdb_key_check.py 你的key
    TMDB_KEY=你的key python3 tmdb_key_check.py
"""
import os, sys, json, requests

key = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TMDB_KEY', '')).strip()
if not key:
    sys.exit('用法: python3 tmdb_key_check.py <你的API Key>')

r = requests.get(f'https://api.themoviedb.org/3/movie/238',
                 params={'api_key': key, 'language': 'zh-CN'}, timeout=20)
print('HTTP', r.status_code)

if r.status_code != 200:
    print(r.text)
    print('\n→ 401 且 status_code=7  : key 填错了/还有空格/被撤销')
    print('→ 401 且无 status_code : 多半是请求根本没到 TMDB（代理或 DNS）')
    sys.exit(1)

d = r.json()
print(f"\n✓ key 有效\n")
print('片名      :', d.get('title'))
print('原始名    :', d.get('original_title'))
print('上映日期  :', d.get('release_date'), '→ 年份', (d.get('release_date') or '')[:4])
print('类型      :', [g['name'] for g in d.get('genres', [])])
print('类型ID    :', [g['id'] for g in d.get('genres', [])])
print('投票数    :', d.get('vote_count'), ' 均分:', d.get('vote_average'))
print('poster_path:', d.get('poster_path'))
print('海报地址  :', 'https://image.tmdb.org/t/p/w500' + (d.get('poster_path') or ''))

pl = requests.get('https://api.themoviedb.org/3/movie/popular',
                  params={'api_key': key, 'page': 1}, timeout=20).json()
print(f"\n/popular 第一页拿到 {len(pl.get('results', []))} 条，"
      f"总页数 {pl.get('total_pages')}，总条数 {pl.get('total_results')}")
print('→ 说明可以用 page 翻页批量拉片单')
