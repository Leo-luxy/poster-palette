#!/usr/bin/env python3
"""采集质量体检：重复、缺失、类型分布、样本是否够分格、海报能不能打开。

输出 data/quality_report.md（可贴进报告附录）。
"""
import csv, os, random
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CSV_PATH = os.path.join(DATA, 'movies.csv')
POSTERS = os.path.join(DATA, 'posters')

GENRE = {28: '动作', 12: '冒险', 16: '动画', 35: '喜剧', 80: '犯罪', 99: '纪录',
         18: '剧情', 10751: '家庭', 14: '奇幻', 36: '历史', 27: '恐怖', 10402: '音乐',
         9648: '悬疑', 10749: '爱情', 878: '科幻', 10770: '电视电影', 53: '惊悚',
         10752: '战争', 37: '西部'}


def main():
    rows = list(csv.DictReader(open(CSV_PATH, encoding='utf-8')))
    n = len(rows)
    ids = [r['id'] for r in rows]
    L = []
    L.append(f'# 采集质量报告\n')
    L.append(f'- 记录数：**{n:,}**　唯一 id：**{len(set(ids)):,}**　重复：{n - len(set(ids))}')
    L.append(f'- 元数据文件：{CSV_PATH}')

    # 采集口径：每年代的实际票数门槛
    cut_path = os.path.join(ROOT, 'outputs', 'a', 'era_cutoff.csv')
    if os.path.exists(cut_path):
        cut = {int(r['year']): int(r['cutoff'])
               for r in csv.DictReader(open(cut_path, encoding='utf-8'))}
        L.append('\n## 0. 采集口径：每年票数门槛（不是固定的 200）\n')
        L.append('按「每年票数前 2.6%」取片，所以门槛随年代变化：')
        L.append('\n| 年代 | 票数门槛 | 入库 | 该年代库里总数 | 通过率 |')
        L.append('| --- | --- | --- | --- | --- |')
        for d in sorted({y // 10 * 10 for y in cut}):
            ys = [y for y in cut if y // 10 * 10 == d]
            lo, hi = min(cut[y] for y in ys), max(cut[y] for y in ys)
            cnt = sum(1 for r in rows if r['year'] and int(r['year']) // 10 * 10 == d)
            tot = int(sum(int(r['total_all']) for r in csv.DictReader(
                open(cut_path, encoding='utf-8')) if int(r['year']) // 10 * 10 == d))
            L.append(f'| {d}s | {lo}–{hi} | {cnt:,} | {tot:,} | {cnt/tot*100:.2f}% |')

    def miss(key, pred):
        c = sum(1 for r in rows if pred(r))
        return f'{c:,}（{c/n*100:.1f}%）'

    L.append('\n## 1. 缺失情况\n')
    L.append('| 字段 | 缺失/异常数 |')
    L.append('| --- | --- |')
    L.append(f'| 年份 | {miss("year", lambda r: not r["year"])} |')
    L.append(f'| 海报 | {miss("poster_path", lambda r: not r["poster_path"])} |')
    L.append(f'| 类型标签 | {miss("genre_ids", lambda r: not r["genre_ids"])} |')
    L.append(f'| 简介 | {miss("overview", lambda r: len(r["overview"]) < 10)} |')
    L.append(f'| 评分为 0 | {miss("vote_average", lambda r: float(r["vote_average"] or 0) == 0)} |')

    # 年份分布
    L.append('\n## 2. 年份分布\n')
    L.append('| 十年 | 数量 |')
    L.append('| --- | --- |')
    dec = Counter(int(r['year']) // 10 * 10 for r in rows if r['year'])
    for d in sorted(dec):
        L.append(f'| {d}s | {dec[d]:,} |')

    # 类型分布
    L.append('\n## 3. 类型分布（多标签，可重复计数）\n')
    gc = Counter()
    for r in rows:
        for g in r['genre_ids'].split('|'):
            if g:
                gc[GENRE.get(int(g), g)] += 1
    L.append('| 类型 | 数量 | 占比 |')
    L.append('| --- | --- | --- |')
    for g, c in gc.most_common():
        L.append(f'| {g} | {c:,} | {c/n*100:.1f}% |')

    # 类型 × 十年（可分格的样本数）
    L.append('\n## 4. 类型 × 十年 样本数（够不够画箱线图，>50 才稳）\n')
    decades = sorted(dec)
    grid = defaultdict(Counter)
    for r in rows:
        if not r['year']:
            continue
        d = int(r['year']) // 10 * 10
        for g in r['genre_ids'].split('|'):
            if g:
                grid[GENRE.get(int(g), g)][d] += 1
    head = '| 类型 | ' + ' | '.join(f'{d}s' for d in decades) + ' |'
    L.append(head)
    L.append('|' + ' --- |' * (len(decades) + 1))
    for g, _ in gc.most_common():
        L.append(f'| {g} | ' + ' | '.join(str(grid[g][d] or '') for d in decades) + ' |')
    thin = [(g, d, grid[g][d]) for g in grid for d in decades if 0 < grid[g][d] < 50]
    L.append(f'\n> 样本数 <50 的格子：**{len(thin)}** 个（这些格子做年代对比要谨慎）')

    # 海报
    L.append('\n## 5. 海报文件\n')
    files = [f for f in os.listdir(POSTERS) if f.endswith('.jpg')]
    size = sum(os.path.getsize(os.path.join(POSTERS, f)) for f in files) if files else 0
    L.append(f'- 文件数：**{len(files):,}**　总大小：**{size/1024/1024:.0f} MB**')
    have = {r['id'] for r in rows if r['poster_path']}
    got = {f[:-4] for f in files}
    L.append(f'- 元数据里有 poster_path 的：{len(have):,}　已下载：{len(got):,}　'
             f'覆盖率：{len(got & have)/max(len(have),1)*100:.1f}%')
    random.seed(0)
    sample = random.sample(files, min(200, len(files)))
    bad, wh = 0, []
    for f in sample:
        try:
            im = Image.open(os.path.join(POSTERS, f))
            wh.append(im.size)
        except Exception:
            bad += 1
    if wh:
        w = np.mean([x[0] for x in wh]); h = np.mean([x[1] for x in wh])
        L.append(f'- 抽检 {len(sample)} 张：损坏 **{bad}** 张，平均尺寸 {w:.0f}×{h:.0f}')

    out = os.path.join(DATA, 'quality_report.md')
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('\n'.join(L))
    print(f'\n→ {out}')


if __name__ == '__main__':
    main()
