#!/usr/bin/env python3
"""小样本试跑：科幻 / 爱情 / 恐怖 三类电影海报的配色差异。

做四件事：
  1. 用 /discover 拉三类各 100 部（1980-2020，评分人数 >= 200）
  2. 下载海报（带缓存）
  3. 提配色指标（饱和度均值、明度均值、色相圆均值、12 扇区色相分布）
  4. 出两张图 + 一份 CSV

关键处理：先按饱和度掩膜掉近灰像素（海报的黑底、白字），否则
K-Means 会把 3 个簇全给"近黑"，统计出来的均值毫无信息。
"""
import csv, os, sys, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from PIL import Image
from matplotlib import pyplot as plt

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

KEY = os.environ.get('TMDB_KEY', '')
API = 'https://api.themoviedb.org/3'
IMG = 'https://image.tmdb.org/t/p/w500'
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
GENRES = {'科幻': 878, '爱情': 10749, '恐怖': 27}
PER_GENRE = 100


def _get(url, **kw):
    """带重试的 GET：代理偶尔会断 SSL，重试三次。"""
    last = None
    for i in range(4):
        try:
            r = requests.get(url, timeout=30, **kw)
            if r.status_code == 200:
                return r
            last = RuntimeError(f'HTTP {r.status_code}')
        except Exception as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


def discover(genre_id, pages):
    out = []
    for p in range(1, pages + 1):
        r = _get(f'{API}/discover/movie', params={
            'api_key': KEY, 'with_genres': genre_id, 'page': p,
            'sort_by': 'vote_count.desc', 'vote_count.gte': 200,
            'primary_release_date.gte': '1980-01-01',
            'primary_release_date.lte': '2020-12-31',
            'include_adult': 'false',
        }).json()
        out += r.get('results', [])
    return out


def metrics(tid, poster_path):
    dst = os.path.join(CACHE, f'{tid}.jpg')
    if not os.path.exists(dst):
        try:
            r = _get(IMG + poster_path)
        except Exception:
            return None
        open(dst, 'wb').write(r.content)
    img = Image.open(dst).convert('RGB')
    w, h = img.size
    img = img.crop((0, 0, w, int(h * 0.88))).resize((120, 160))   # 切掉底部演职员表
    hsv = np.asarray(img.convert('HSV')).astype(np.float64)
    H = hsv[:, :, 0] * 360 / 255
    S = hsv[:, :, 1] / 255
    V = hsv[:, :, 2] / 255
    mask = S >= 0.20
    sat_frac = mask.mean()
    if mask.sum() < 200:
        hue = np.nan
    else:
        wgt = S[mask]
        hue = (np.degrees(np.arctan2((np.sin(np.radians(H[mask])) * wgt).mean(),
                                     (np.cos(np.radians(H[mask])) * wgt).mean())) % 360)
    return {'mean_s': S.mean(), 'mean_v': V.mean(), 'sat_frac': sat_frac,
            'hue': hue, 'hue_hist': np.histogram(H[mask], bins=12, range=(0, 360))[0].tolist()
            if mask.sum() >= 200 else [0] * 12}


def main():
    if not KEY:
        sys.exit('请先 export TMDB_KEY=...')
    os.makedirs(CACHE, exist_ok=True)

    rows = []
    for g, gid in GENRES.items():
        items = discover(gid, PER_GENRE // 20)
        print(f'{g}: {len(items)} 部')
        for m in items:
            rows.append({'tmdb_id': m['id'], 'title': m['title'], 'genre': g,
                         'year': int((m.get('release_date') or '0')[:4] or 0),
                         'poster_path': m.get('poster_path') or '',
                         'vote_count': m.get('vote_count', 0)})

    todo = [r for r in rows if r['poster_path']]
    print(f'有海报 {len(todo)}/{len(rows)}')
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda r: metrics(r['tmdb_id'], r['poster_path']), todo))
    print(f'下载+提色 {time.time()-t0:.0f}s')
    for r, m in zip(todo, res):
        r['ok'] = m is not None
        if m:
            r.update(m)

    ok = [r for r in todo if r.get('ok')]
    out = os.path.join(HERE, 'pilot_color.csv')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['tmdb_id', 'title', 'genre', 'year', 'vote_count',
                                          'mean_s', 'mean_v', 'sat_frac', 'hue'] + [f'h{i}' for i in range(12)])
        w.writeheader()
        for r in ok:
            row = {k: r.get(k) for k in ['tmdb_id', 'title', 'genre', 'year', 'vote_count',
                                         'mean_s', 'mean_v', 'sat_frac', 'hue']}
            for i, v in enumerate(r.get('hue_hist') or [0] * 12):
                row[f'h{i}'] = v
            w.writerow(row)

    print(f'\n有效样本 {len(ok)}')
    for g in GENRES:
        sub = [r for r in ok if r['genre'] == g]
        if sub:
            print(f'  {g:4s} n={len(sub):3d}  饱和度 {np.mean([r["mean_s"] for r in sub]):.3f}  '
                  f'明度 {np.mean([r["mean_v"] for r in sub]):.3f}  '
                  f'色相 {np.nanmean([r["hue"] for r in sub]):.1f}°')

    # 图 1：饱和度 / 明度按类型十年
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    decades = sorted({r['year'] // 10 * 10 for r in ok})
    for ax, key, name in [(axes[0], 'mean_s', '平均饱和度'), (axes[1], 'mean_v', '平均明度')]:
        for g in GENRES:
            xs, ys = [], []
            for d in decades:
                v = [r[key] for r in ok if r['genre'] == g and r['year'] // 10 * 10 == d]
                if len(v) >= 5:
                    xs.append(d); ys.append(np.mean(v))
            ax.plot(xs, ys, 'o-', label=g, linewidth=2)
        ax.set_title(f'三类电影海报的{name}（按十年）', fontsize=13)
        ax.set_xlabel('年代'); ax.set_ylabel(name); ax.legend(); ax.grid(alpha=.25)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, 'pilot_sat_valence.png'), dpi=150, facecolor='white')

    # 图 2：色相 12 扇区对比
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': 'polar'})
    for g in GENRES:
        sub = [r for r in ok if r['genre'] == g and r.get('hue_hist')]
        if not sub:
            continue
        agg = np.sum([r['hue_hist'] for r in sub], axis=0).astype(float)
        agg /= agg.sum()
        theta = np.radians(np.arange(0, 360, 30) + 15)
        ax.bar(theta, agg, width=np.radians(28), label=g, alpha=.55)
    ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
    ax.set_title('海报色相分布（12 扇区，权重=饱和度）', fontsize=13, pad=18)
    ax.legend(loc='lower right', bbox_to_anchor=(1.15, 0.15))
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, 'pilot_hue.png'), dpi=150, facecolor='white')
    print('→ pilot_color.csv / pilot_sat_valence.png / pilot_hue.png')


if __name__ == '__main__':
    main()
