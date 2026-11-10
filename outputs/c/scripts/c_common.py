from pathlib import Path
import hashlib, json, platform, re, subprocess, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import scipy, matplotlib

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs' / 'c'
TABLES = OUT / 'tables'
INPUTS = ['movies.csv', 'color_features.csv', 'movie_details.csv', 'yearly.csv']
METRICS = ['mean_v', 'mean_s', 'colorful']
GROUPS = ['US', 'GB', 'FR', 'IT', 'JP', 'ZH', 'KR']
SEED = 42
CANDIDATES = {'en':'US GB CA AU IE NZ', 'fr':'FR BE CA CH LU', 'it':'IT CH', 'de':'DE AT CH', 'es':'ES MX AR CL CO CU PE UY', 'zh':'CN HK TW', 'cn':'CN HK TW', 'ja':'JP', 'ko':'KR', 'hi':'IN', 'ru':'RU SU', 'pt':'BR PT', 'sv':'SE', 'da':'DK', 'no':'NO', 'pl':'PL'}
CANDIDATES = {k: set(v.split()) for k, v in CANDIDATES.items()}
PRIMARY = {'en':'US', 'fr':'FR', 'it':'IT', 'de':'DE'}

def fingerprints():
    return {f: hashlib.sha256((ROOT / 'data' / f).read_bytes()).hexdigest() for f in INPUTS}

def load_safe():
    TABLES.mkdir(parents=True, exist_ok=True)
    hashes = fingerprints()
    manifest = OUT / 'run_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text(encoding='utf-8'))['input_sha256'] != hashes:
        raise RuntimeError('输入指纹与上次运行不一致；请先核实数据版本，不要覆盖原记录。')
    m = pd.read_csv(ROOT/'data/movies.csv', dtype={'id':'int64'})
    f = pd.read_csv(ROOT/'data/color_features.csv', dtype={'tmdb_id':'int64'})
    d = pd.read_csv(ROOT/'data/movie_details.csv', dtype={'id':'int64'})
    for df, key in [(m,'id'), (f,'tmdb_id'), (d,'id')]:
        if df[key].isna().any() or df[key].duplicated().any():
            raise ValueError(f'主键缺失或重复: {key}')
    missing_features = m.loc[~m.id.isin(f.tmdb_id), ['id']]
    orphan_features = f.loc[~f.tmdb_id.isin(m.id), ['tmdb_id']]
    missing_details = m.loc[~m.id.isin(d.id), ['id']]
    missing_features.to_csv(TABLES/'missing_features.csv', index=False, encoding='utf-8')
    orphan_features.to_csv(TABLES/'orphan_features.csv', index=False, encoding='utf-8')
    missing_details.to_csv(TABLES/'missing_details.csv', index=False, encoding='utf-8')
    x = m.merge(f, left_on='id', right_on='tmdb_id', validate='one_to_one').merge(d[['id','production_countries']], on='id', how='left', validate='one_to_one', indicator='details_match')
    if len(x) != 19694 or not x.id.is_unique or not x.year.between(1950,2025).all():
        raise RuntimeError(f'输入不符合已核对基线：{len(x)} 行；请核实版本和年份。')
    x['decade'] = x.year // 10 * 10
    issues = []
    for _, row in x.iterrows():
        raw = row.production_countries
        if pd.notna(raw):
            parts = [s.strip() for s in str(raw).split('|') if s.strip()]
            if any(not re.fullmatch(r'[A-Z]{2}', s) for s in parts):
                issues.append({'id': row.id, 'production_countries': raw})
    pd.DataFrame(issues, columns=['id','production_countries']).to_csv(TABLES/'country_format_issues.csv',index=False,encoding='utf-8')
    if issues:
        raise ValueError('存在异常国家码，详见 country_format_issues.csv')
    checks = []
    for col in METRICS + ['sat_frac']:
        v = pd.to_numeric(x[col], errors='coerce')
        valid = v[np.isfinite(v)]
        bad = (~np.isfinite(v)) | (v < 0) | ((v > 1) if col != 'colorful' else False)
        checks.append({'metric':col, 'n_valid':len(valid), 'n_missing_or_nonfinite':int((~np.isfinite(v)).sum()), 'n_out_of_range':int((bad & np.isfinite(v)).sum()), 'min':valid.min(), 'max':valid.max()})
    pd.DataFrame(checks).to_csv(TABLES/'metric_audit.csv',index=False,encoding='utf-8')
    if any(c['n_out_of_range'] for c in checks):
        raise ValueError('指标超出预期范围，见 metric_audit.csv')
    return x

def save_manifest():
    def git(*args):
        p = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return p.stdout.strip() if p.returncode == 0 else None
    data = {'input_sha256':fingerprints(), 'git_commit':git('rev-parse','HEAD'), 'git_status_short':git('status','--short','--untracked-files=all'), 'software':{'python':sys.version, 'platform':platform.platform(), 'pandas':pd.__version__, 'numpy':np.__version__, 'scipy':scipy.__version__, 'matplotlib':matplotlib.__version__}, 'config':{'seed':SEED, 'bootstrap_iterations':1000, 'time_years':[1950,2025], 'country_years':[2001,2025], 'groups':GROUPS, 'sat_frac_min':0.10, 'language_candidates':{k:sorted(v) for k,v in CANDIDATES.items()}, 'primary':PRIMARY}, 'run_utc':datetime.now(timezone.utc).isoformat()}
    (OUT/'run_manifest.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')

def mapped(c):
    return 'ZH' if c in {'CN','HK','TW'} else 'RU' if c in {'RU','SU'} else c

def assign(raw, language):
    countries = sorted(set(s.strip() for s in str(raw).split('|') if s.strip())) if pd.notna(raw) else []
    lang = str(language).lower() if pd.notna(language) else ''
    regions = sorted({mapped(c) for c in countries})
    candidates = sorted({mapped(c) for c in set(countries) & CANDIDATES.get(lang,set())})
    primary = PRIMARY.get(lang, '')
    hit = primary if primary and primary in candidates else ''
    if not countries: group, rule = 'NONE', 'none'
    elif len(countries) == 1: group, rule = regions[0], 'solo'
    elif len(regions) == 1: group, rule = regions[0], 'region_merged'
    elif len(candidates) == 1: group, rule = candidates[0], 'lang_unique'
    elif len(candidates) > 1 and hit: group, rule = hit, 'lang_primary'
    else: group, rule = 'AMBIG', 'ambig'
    return '|'.join(countries), len(countries), int(len(countries)>1), group, rule, '|'.join(candidates), hit

# Bootstrap 每次按电影独立重采样；每项计算使用稳定的种子。
def bootstrap(values, seed=SEED):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a): return (np.nan,)*4
    rng = np.random.default_rng(seed)
    means, medians = [], []
    for _ in range(1000):
        b = rng.choice(a, size=len(a), replace=True)
        means.append(np.mean(b)); medians.append(np.median(b))
    return (*np.percentile(means,[2.5,97.5]), *np.percentile(medians,[2.5,97.5]))

def describe(frame, bootstrap_ci=False):
    result = {'n_total':len(frame), 'sat_frac_median':frame.sat_frac.median(), 'near_gray_frac':(frame.sat_frac < .10).sum()/len(frame) if len(frame) else np.nan}
    for metric in METRICS:
        a = pd.to_numeric(frame[metric],errors='coerce').to_numpy(dtype=float)
        a = a[np.isfinite(a)]
        result.update({f'{metric}_n_valid':len(a), f'{metric}_mean':np.mean(a) if len(a) else np.nan, f'{metric}_median':np.median(a) if len(a) else np.nan, f'{metric}_q1':np.percentile(a,25) if len(a) else np.nan, f'{metric}_q3':np.percentile(a,75) if len(a) else np.nan})
        if bootstrap_ci:
            lo, hi, ml, mh = bootstrap(a)
            result.update({f'{metric}_mean_ci_low':lo, f'{metric}_mean_ci_high':hi, f'{metric}_median_ci_low':ml, f'{metric}_median_ci_high':mh})
    return result

def contrast(a,b,metric):
    a = np.asarray(a[metric],dtype=float); a = a[np.isfinite(a)]
    b = np.asarray(b[metric],dtype=float); b = b[np.isfinite(b)]
    rng = np.random.default_rng(SEED)
    ds = [rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean() for _ in range(1000)]
    return {'metric':metric, 'n_a':len(a), 'n_b':len(b), 'mean_difference':a.mean()-b.mean(), 'ci_low':np.percentile(ds,2.5), 'ci_high':np.percentile(ds,97.5)}

def hue_summary(frame, dimension, label):
    h = frame[[f'h{i}' for i in range(12)]].to_numpy(dtype=float)
    valid = np.isfinite(h).all(axis=1) & (h >= 0).all(axis=1) & (h.sum(axis=1)>0)
    eligible = (frame.sat_frac.to_numpy() >= .10)
    good = valid & eligible
    norm = h[good] / h[good].sum(axis=1,keepdims=True)
    row = {'dimension':dimension,'group':str(label),'n_total':len(frame),'n_hue':int(good.sum()),'n_invalid_eligible':int((eligible & ~valid).sum()),'near_gray_frac':int((frame.sat_frac < .10).sum())/len(frame)}
    row.update({f'h{i}':norm[:,i].mean() if len(norm) else np.nan for i in range(12)})
    row['sat_frac_threshold'] = .10
    return row, frame.loc[eligible & ~valid, ['id']]

def update_shared(filename, dimension, rows):
    path = TABLES/filename
    new = pd.DataFrame(rows)
    if path.exists():
        old = pd.read_csv(path, dtype={'group':str})
        new = pd.concat([old[old.dimension != dimension],new],ignore_index=True)
    new.to_csv(path,index=False,encoding='utf-8')
