from pathlib import Path
import tempfile, shutil, subprocess, sys, argparse, os
import pandas as pd
from c_adv_common import ROOT,OUT

def main():
 p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); a=p.parse_args()
 if not all(c.isalnum() or c in '-_' for c in a.run_id): raise ValueError('Invalid run ID')
 out=OUT/'tables/advanced'/a.run_id; log=[]
 with tempfile.TemporaryDirectory(prefix='legacy_check_',dir=out) as tmp:
  t=Path(tmp); (t/'data/posters').mkdir(parents=True); (t/'outputs/c/scripts').mkdir(parents=True); (t/'outputs/c/tables').mkdir(); (t/'outputs/c/reports').mkdir(); (t/'outputs/c/ppt').mkdir(); (t/'figures/c').mkdir(parents=True)
  for path in (ROOT/'data').glob('*.csv'): shutil.copy2(path,t/'data'/path.name)
  for path in (ROOT/'outputs/c/scripts').glob('*.py'): shutil.copy2(path,t/'outputs/c/scripts'/path.name)
  for path in (ROOT/'outputs/c/tables').glob('*.csv'): shutil.copy2(path,t/'outputs/c/tables'/path.name)
  for path in (ROOT/'outputs/c/ppt').glob('*.png'): shutil.copy2(path,t/'outputs/c/ppt'/path.name)
  for path in (ROOT/'figures/c').glob('*.png'): shutil.copy2(path,t/'figures/c'/path.name)
  shutil.copy2(ROOT/'outputs/c/run_manifest.json',t/'outputs/c/run_manifest.json')
  for id in pd.read_csv(ROOT/'outputs/c/tables/palette_examples.csv').id.unique(): shutil.copy2(ROOT/f'data/posters/{id}.jpg',t/f'data/posters/{id}.jpg')
  commands=[[sys.executable,str(t/'outputs/c/scripts'/script)] for script in ['c01_country_group.py','c02_time.py','c03_country.py','c04_palettes.py','c05_comparisons.py']]+[[sys.executable,str(t/'outputs/c/scripts/c99_validate.py'),'--stage',stage] for stage in ['time','all']]
  for cmd in commands:
   label=('validation '+cmd[-1]) if '--stage' in cmd else Path(cmd[1]).name; r=subprocess.run(cmd,cwd=t,capture_output=True,text=True,encoding='utf8',errors='replace',env={**os.environ,'PYTHONIOENCODING':'utf-8'}); log.append(f'{label}: exit {r.returncode}\n{r.stdout}\n{r.stderr}')
   if r.returncode: break
 (out/'legacy_validation_log.txt').write_text('\n\n'.join(log).rstrip()+'\n',encoding='utf8'); print('\n'.join(s.splitlines()[0] for s in log));
 if len(log)!=7 or any('exit 0' not in s for s in log): raise SystemExit(1)
if __name__=='__main__': main()
