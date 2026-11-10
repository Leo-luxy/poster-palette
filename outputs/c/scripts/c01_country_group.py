import pandas as pd
from c_common import load_safe, assign, save_manifest, TABLES, GROUPS

def main():
    x = load_safe()
    cols = ['countries_raw','n_countries_raw','is_coprod','country_main','rule','assignment_candidates','primary_hit']
    assigned = pd.DataFrame([assign(a,b) for a,b in zip(x.production_countries,x.original_language)], columns=cols, index=x.index)
    group = pd.concat([x[['id','year','decade','original_language']],assigned],axis=1).sort_values('id')
    assert group.id.is_unique and len(group) == len(x)
    group.to_csv(TABLES/'country_group.csv',index=False,encoding='utf-8')
    group.groupby(['rule','country_main'],dropna=False).size().rename('n').reset_index().to_csv(TABLES/'assignment_summary.csv',index=False,encoding='utf-8')
    recent = group[group.year.between(2001,2025)]
    recent.groupby(['rule','country_main'],dropna=False).size().rename('n').reset_index().to_csv(TABLES/'assignment_summary_2001_2025.csv',index=False,encoding='utf-8')
    support = recent.groupby(['country_main','decade']).size().rename('n').reset_index()
    support['low_n'] = support.n < 30
    support.to_csv(TABLES/'sample_support.csv',index=False,encoding='utf-8')
    print('全部归属规则:', group.rule.value_counts().to_dict())
    print('2001—2025 七组:', recent.country_main.value_counts().reindex(GROUPS,fill_value=0).to_dict())
    print('缺少国家:', (group.rule=='none').sum())
    save_manifest()
if __name__ == '__main__': main()
