import pandas as pd
from c_common import load_safe, describe, contrast, hue_summary, update_shared, TABLES, GROUPS, METRICS

def main():
    x=load_safe().merge(pd.read_csv(TABLES/'country_group.csv',keep_default_na=False)[['id','country_main']],on='id',validate='one_to_one')
    x=x[x.year.between(2001,2025) & x.country_main.isin(GROUPS)]
    summary=[]; hues=[]; invalid=[]; contrasts=[]
    for group in GROUPS:
        g=x[x.country_main==group]
        summary.append({'country_main':group,**describe(g,True)})
        row,bad=hue_summary(g,'country',group); hues.append(row); invalid.append(bad.assign(dimension='country',group=group))
        if group!='US':
            for m in METRICS:
                contrasts.append({'dimension':'country','group_a':group,'group_b':'US','range_a':'2001-2025','range_b':'2001-2025',**contrast(g,x[x.country_main=='US'],m)})
    pd.DataFrame(summary).to_csv(TABLES/'country_summary.csv',index=False,encoding='utf-8')
    pd.concat(invalid).to_csv(TABLES/'hue_invalid_country.csv',index=False,encoding='utf-8')
    update_shared('hue_summary.csv','country',hues)
    update_shared('contrasts.csv','country',contrasts)
    print('国家分析:',len(x),'部；七组统计及 18 项差值完成。')
if __name__=='__main__':
    main()
    from c_plot import make
    make('country')
