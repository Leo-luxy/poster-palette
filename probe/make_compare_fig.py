#!/usr/bin/env python3
"""生成「现有海报 vs 原语言候选」对照图。"""
import csv, os, urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'outputs', 'a')
CAND = os.path.join(ROOT, 'probe', 'cache', 'cand')
IMG = 'https://image.tmdb.org/t/p/w342'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'

# 片名 / 年份 / 国家 / 现有所属 / 候选
FILMS = [(11224, '仙履奇缘', 1950, '美国'), (599, '日落大道', 1950, '美国'),
         (3782, '生之欲', 1952, '日本'), (100, '两杆大烟枪', 1998, '英国'),
         (496243, '寄生虫', 2019, '韩国')]


def key():
    for l in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
        if l.startswith('TMDB_KEY='):
            return l.split('=', 1)[1].strip()


def api(path, **p):
    import json, urllib.parse
    p['api_key'] = key()
    with urllib.request.urlopen('https://api.themoviedb.org/3' + path + '?' + urllib.parse.urlencode(p), timeout=30) as r:
        return json.loads(r.read().decode())


def choose(mid, orig):
    d = api(f'/movie/{mid}/images', include_image_language=f'{orig},en,null,zh')
    ps = d.get('posters', [])
    picks = {}
    for tag, lang in (('orig', orig), ('textless', None), ('en', 'en')):
        c = [p for p in ps if p.get('iso_639_1') == lang]
        if c:
            c.sort(key=lambda p: (p.get('vote_average') or 0, p.get('width') or 0), reverse=True)
            picks[tag] = c[0]['file_path']
    return picks


def fetch(path, dst):
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return Image.open(dst).convert('RGB')
    urllib.request.urlretrieve(IMG + path, dst)
    return Image.open(dst).convert('RGB')


def main():
    os.makedirs(CAND, exist_ok=True)
    W, H = 342, 513
    pad, head, cap = 24, 96, 56
    rows = len(FILMS)
    cols = 3
    canvas = Image.new('RGB', (pad + cols * (W + pad), head + rows * (H + cap + pad)), 'white')
    d = ImageDraw.Draw(canvas)
    f24 = ImageFont.truetype(FONT, 24)
    f18 = ImageFont.truetype(FONT, 18)
    d.text((pad, 28), '同一部电影的三种海报：现有(zh) / 原语言 / 无文字', font=f24, fill='black')
    heads = ['现有海报（当前流水线用的）', '原语言海报（候选替换）', '无文字海报（textless）']
    for j, h in enumerate(heads):
        d.text((pad + j * (W + pad), head - 34), h, font=f18, fill=(90, 90, 90))

    for i, (mid, title, year, country) in enumerate(FILMS):
        cur = Image.open(os.path.join(DATA, 'posters', f'{mid}.jpg')).convert('RGB').resize((W, H))
        orig = api(f'/movie/{mid}', language='en-US').get('original_language')
        picks = choose(mid, orig)
        y = head + i * (H + cap + pad)
        canvas.paste(cur, (pad, y))
        labels = ['zh', orig, '无文字']
        for j, tag in enumerate(['orig', 'textless']):
            x = pad + (j + 1) * (W + pad)
            if tag in picks:
                im = fetch(picks[tag], os.path.join(CAND, f'{mid}_{tag}.jpg')).convert('RGB').resize((W, H))
                canvas.paste(im, (x, y))
            else:
                d.rectangle([x, y, x + W, y + H], fill=(235, 235, 235))
                d.text((x + W // 2 - 40, y + H // 2), '无', font=f24, fill=(120, 120, 120))
        # 行标签
        d.text((pad, y + H + 8), f'{title}（{year}，{country}）  现有标签: zh', font=f18, fill='black')
        for j, tag in enumerate(['orig', 'textless']):
            if tag in picks:
                d.text((pad + (j + 1) * (W + pad), y + H + 8), f'候选标签: {labels[j + 1]}', font=f18, fill=(60, 60, 60))
        print(mid, title, picks)

    p = os.path.join(OUT, 'poster_lang_compare.png')
    canvas.save(p)
    print('→', p, canvas.size)


if __name__ == '__main__':
    main()
