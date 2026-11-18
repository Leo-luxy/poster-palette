import argparse, json
from datetime import datetime,timezone
from c_adv_common import ROOT,OUT,sha,write_manifest

def main():
 p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); a=p.parse_args()
 if not all(c.isalnum() or c in '-_' for c in a.run_id): raise ValueError('Invalid run ID')
 out=OUT/'tables/advanced'/a.run_id; m=json.loads((out/'manifest.json').read_text(encoding='utf8')); m['code_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted((OUT/'scripts').glob('*.py')) if p.name.startswith(('c06_','c07_','c08_','c09_','c_adv_','c99_','c_legacy_','test_advanced_'))}; m['code_sha256']['outputs/c/scripts/c_adv_config.json']=sha(OUT/'scripts/c_adv_config.json'); m['completed_utc']=datetime.now(timezone.utc).isoformat(); m['stages']['c08']['failures']=0; n=m['stages']['c09']['complete_cases']; m['stages']['c09']['excluded_complete_case']={k:(19694 if k.endswith('_time') else 10115)-v for k,v in n.items()}; write_manifest(out,m)
if __name__=='__main__': main()
