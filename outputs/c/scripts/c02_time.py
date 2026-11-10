import numpy as np
import pandas as pd
from scipy.stats import spearmanr, theilslopes
from c_common import load_safe, describe, contrast, hue_summary, update_shared, TABLES, METRICS

def main():
    x = load_safe()
    pd.DataFrame([{'sector':f'h{i}','start_degrees':30*i,'end_degrees_exclusive':30*(i+1)} for i in range(12)]).to_csv(TABLES/'hue_sectors.csv',index=False,encoding='utf-8')
    x = x[x.year.between(1950,2025)]
    annual=[]
    for year, g in x.groupby('year',sort=True):
        row={'year':int(year),**describe(g),'window_start':year-2 if 1952<=year<=2023 else np.nan,'window_end':year+2 if 1952<=year<=2023 else np.nan}
        w=x[x.year.between(year-2,year+2)] if 1952<=year<=2023 else x.iloc[0:0]
        row['n_window']=len(w) if len(w) else np.nan
        for m in METRICS:
            for name, q in [('median',.5),('q1',.25),('q3',.75)]: row[f'{m}_window_{name}']=w[m].quantile(q) if len(w) else np.nan
        annual.append(row)
    annual=pd.DataFrame(annual); annual.to_csv(TABLES/'time_yearly.csv',index=False,encoding='utf-8')
    old=pd.read_csv('data/yearly.csv')
    check=annual.merge(old,on='year',validate='one_to_one')
    assert len(check)==76 and (check.n_total==check.n).all(), '年度样本数不符'
    for metric, col in [('mean_v','med_v'),('mean_s','med_s'),('colorful','med_colorful')]:
        diff=(check[f'{metric}_median']-check[col]).abs()
        if (diff > (0.0050001 if metric=='colorful' else 0.00010001)).any(): raise ValueError(f'年度中位数不符: {metric}, max={diff.max()}')
    decades=[]; hues=[]; invalid=[]
    for decade,g in x.groupby('decade',sort=True):
        decades.append({'decade':int(decade),**describe(g,True)})
        row, bad=hue_summary(g,'time',int(decade)); hues.append(row); invalid.append(bad.assign(dimension='time',group=int(decade)))
    pd.DataFrame(decades).to_csv(TABLES/'time_decade.csv',index=False,encoding='utf-8')
    pd.concat(invalid).to_csv(TABLES/'hue_invalid_time.csv',index=False,encoding='utf-8')
    update_shared('hue_summary.csv','time',hues)
    contrasts=[]
    for a,b in [(2010,1950),(2020,2010)]:
        for m in METRICS:
            contrasts.append({'dimension':'time','group_a':str(a),'group_b':str(b),'range_a':'2020-2025' if a==2020 else f'{a}-{a+9}','range_b':f'{b}-{b+9}',**contrast(x[x.decade==a],x[x.decade==b],m)})
    update_shared('contrasts.csv','time',contrasts)
    trends=[]
    for m in METRICS:
        z=annual[annual[f'{m}_n_valid']>=30].dropna(subset=[f'{m}_median'])
        rho=spearmanr(z.year,z[f'{m}_median']).statistic
        slope=theilslopes(z[f'{m}_median'],z.year).slope*10
        trends.append({'metric':m,'range':'1950-2025','n_years':len(z),'spearman_rho':rho,'theil_sen_per_decade':slope})
    pd.DataFrame(trends).to_csv(TABLES/'time_trend.csv',index=False,encoding='utf-8')
    print('时间分析:',len(x),'部，',len(annual),'年；年度统计核对通过。')
if __name__=='__main__':
    main()
    from c_plot import make
    make('time')
