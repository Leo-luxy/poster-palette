from pathlib import Path
import hashlib, json, platform, subprocess, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import scipy, matplotlib, PIL, sklearn
from c_common import ROOT, OUT

GROUPS = ['FR','GB','IT','JP','KR','US','ZH']
COUNTRY_GROUP_BASELINE_SHA256 = 'b36fb3d14e386e2c71fc9fd9dbba2c817bad76749de724275852db42e5723e27'
INPUTS = [ROOT/'data/movies.csv',ROOT/'data/color_features.csv',ROOT/'data/movie_details.csv',OUT/'tables/country_group.csv']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def setup(run_id, config_path):
    if not run_id or not all(c.isalnum() or c in '-_' for c in run_id): raise ValueError('Invalid run ID')
    config=json.loads(Path(config_path).read_text(encoding='utf-8'))
    out=OUT/'tables/advanced'/run_id; out.mkdir(parents=True,exist_ok=True)
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in INPUTS}
    if hashes['outputs/c/tables/country_group.csv'] != COUNTRY_GROUP_BASELINE_SHA256: raise RuntimeError('Country group fingerprint differs from verified baseline; investigate before updating the baseline.')
    manifest_path=out/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['config'] != config or manifest['input_sha256'] != hashes: raise RuntimeError('Run ID already has different configuration or inputs; investigate and use a new run ID.')
    else:
        baseline=json.loads((OUT/'run_manifest.json').read_text(encoding='utf-8'))['input_sha256']
        for p in INPUTS[:3]:
            if hashes[str(p.relative_to(ROOT)).replace('\\','/')] != baseline[p.name]: raise RuntimeError('Input fingerprint differs from existing baseline: '+p.name)
        def git(*args):
            r=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace')
            return r.stdout.strip() if r.returncode==0 else None
        manifest={'config':config,'input_sha256':hashes,'git_commit':git('rev-parse','HEAD'),'git_status':git('status','--short','--untracked-files=all'),'software':{'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'Pillow':PIL.__version__,'scikit-learn':sklearn.__version__},'created_utc':datetime.now(timezone.utc).isoformat(),'stages':{}}
        write_manifest(out,manifest)
    return out,config,manifest

def write_manifest(out,manifest):
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def load(out):
    m=pd.read_csv(INPUTS[0],dtype={'id':'int64'}); f=pd.read_csv(INPUTS[1],dtype={'tmdb_id':'int64'}); d=pd.read_csv(INPUTS[2],dtype={'id':'int64'}); cg=pd.read_csv(INPUTS[3],dtype={'id':'int64'},keep_default_na=False)
    for df,k in [(m,'id'),(f,'tmdb_id'),(d,'id'),(cg,'id')]:
        if df[k].isna().any() or df[k].duplicated().any(): raise ValueError('Invalid primary key: '+k)
    for name, ids in [('missing_features',m.loc[~m.id.isin(f.tmdb_id),'id']),('orphan_features',f.loc[~f.tmdb_id.isin(m.id),'tmdb_id']),('missing_details',m.loc[~m.id.isin(d.id),'id'])]: ids.to_frame('id').to_csv(out/(name+'.csv'),index=False)
    x=m.merge(f,left_on='id',right_on='tmdb_id',validate='one_to_one').merge(d[['id','production_countries']],on='id',how='left',validate='one_to_one').merge(cg[['id','country_main','rule']],on='id',how='left',validate='one_to_one',indicator='country_match')
    if len(x)!=19694 or not x.year.between(1950,2025).all() or (x.country_match!='both').any(): raise RuntimeError('Input does not match validated baseline')
    if len(x[x.year.between(2001,2025)&x.country_main.isin(GROUPS)]) != 10115: raise RuntimeError('Country sample differs from validated baseline')
    x['decade']=x.year//10*10
    x=x.sort_values('id').reset_index(drop=True)
    g=x[['id','genre_ids']].copy(); g['genre_ids']=g.genre_ids.fillna('').astype(str).str.findall(r'\d+'); g=g.explode('genre_ids').dropna().drop_duplicates(); g.rename(columns={'genre_ids':'genre_id'}).to_csv(out/'genre_membership.csv',index=False)
    return x

def rgb_to_lab(rgb):
    rgb=np.asarray(rgb,dtype=float); lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    xyz=lin @ np.array([[.4124564,.2126729,.0193339],[.3575761,.7151522,.1191920],[.1804375,.0721750,.9503041]])
    xyz=xyz/np.array([.95047,1.,1.08883]); delta=6/29
    t=np.where(xyz>delta**3,np.cbrt(xyz),xyz/(3*delta**2)+4/29)
    return np.stack([116*t[...,1]-16,500*(t[...,0]-t[...,1]),200*(t[...,1]-t[...,2])],axis=-1)
