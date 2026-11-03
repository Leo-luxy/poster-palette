#!/usr/bin/env python3
"""配色特征提取：把每张海报压成一行数字。

核心约束：先按饱和度掩膜掉近灰像素（黑底、白字、银幕反光），否则
K-Means 会把三个簇全给「近黑」，统计出来的均值毫无信息。

输出 data/color_features.csv，字段：
  mean_s 平均饱和度 / mean_v 平均明度 / v_std 明暗对比 / sat_frac 高饱和像素占比
  hue 色相圆均值(度) / h0..h11 12 扇区色相占比
  colorful 色彩丰富度(Hasler-Süsstrunk) / dom1..3 主色 HEX / ds1..3 占比
"""
import csv, os, sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
POSTERS = os.path.join(DATA, 'posters')
OUT = os.path.join(DATA, 'color_features.csv')
SAT_MIN = 0.20          # 近灰掩膜阈值
CROP_BOTTOM = 0.12      # 切掉底部演职员表

FIELDS = (['tmdb_id', 'mean_s', 'mean_v', 'v_std', 'sat_frac', 'hue', 'colorful']
          + [f'h{i}' for i in range(12)] + ['dom1', 'dom2', 'dom3', 'ds1', 'ds2', 'ds3'])


def features(path):
    img = Image.open(path).convert('RGB')
    w, h = img.size
    img = img.crop((0, 0, w, int(h * (1 - CROP_BOTTOM)))).resize((120, 160))
    rgb = np.asarray(img).astype(np.float64)
    hsv = np.asarray(img.convert('HSV')).astype(np.float64)
    H, S, V = hsv[:, :, 0] * 360 / 255, hsv[:, :, 1] / 255, hsv[:, :, 2] / 255

    mask = S >= SAT_MIN
    sat_frac = float(mask.mean())

    # 色彩丰富度（Hasler & Süsstrunk 2003）
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    rg, yb = R - G, (R + G) / 2 - B
    colorful = float(np.sqrt(rg.std() ** 2 + yb.std() ** 2)
                     + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))

    row = {'mean_s': round(float(S.mean()), 4), 'mean_v': round(float(V.mean()), 4),
           'v_std': round(float(V.std()), 4), 'sat_frac': round(sat_frac, 4),
           'colorful': round(colorful, 2)}

    if mask.sum() < 200:                       # 近乎纯灰的海报，色相无意义
        row['hue'] = ''
        for i in range(12):
            row[f'h{i}'] = 0
        for i in (1, 2, 3):
            row[f'dom{i}'] = ''
            row[f'ds{i}'] = 0
        return row

    wgt = S[mask]
    row['hue'] = round(float(np.degrees(np.arctan2(
        (np.sin(np.radians(H[mask])) * wgt).mean(),
        (np.cos(np.radians(H[mask])) * wgt).mean())) % 360), 2)

    hist, _ = np.histogram(H[mask], bins=12, range=(0, 360))
    hist = hist / hist.sum()
    for i, v in enumerate(hist):
        row[f'h{i}'] = round(float(v), 4)

    # 掩膜后 K-Means 取 3 个主色
    X = rgb[mask]
    if len(X) > 3000:
        idx = np.random.default_rng(0).choice(len(X), 3000, replace=False)
        X = X[idx]
    km = KMeans(n_clusters=3, n_init=4, random_state=0).fit(X)
    share = np.bincount(km.labels_, minlength=3) / len(X)
    order = share.argsort()[::-1]
    for k, i in enumerate(order):
        r, g, b = km.cluster_centers_[i].round().astype(int)
        row[f'dom{k+1}'] = f'#{r:02x}{g:02x}{b:02x}'
        row[f'ds{k+1}'] = round(float(share[i]), 4)
    return row


def work(fname):
    tid = int(fname[:-4])
    try:
        return tid, features(os.path.join(POSTERS, fname))
    except Exception as e:
        return tid, {'error': str(e)[:60]}


def main():
    files = sorted(f for f in os.listdir(POSTERS) if f.endswith('.jpg'))
    print(f'待处理 {len(files)} 张')
    rows, err = [], 0
    # 进程数可用 WORKERS 环境变量调低（机器还要用的时候：WORKERS=2 nice -n 19 python3 ...）
    with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 6))) as ex:
        for i, (tid, feat) in enumerate(ex.map(work, files, chunksize=64), 1):
            if 'error' in feat:
                err += 1
                continue
            feat['tmdb_id'] = tid
            rows.append(feat)
            if i % 2000 == 0:
                print(f'  {i}/{len(files)}', flush=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})
    print(f'完成：{len(rows)} 行，失败 {err} → {OUT}')


if __name__ == '__main__':
    main()
