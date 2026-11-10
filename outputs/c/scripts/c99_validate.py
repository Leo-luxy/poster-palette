import argparse
import numpy as np
import pandas as pd
from PIL import Image
from c_common import ROOT, OUT, TABLES, load_safe, GROUPS, METRICS, assign, contrast

def main():
    p=argparse.ArgumentParser(); p.add_argument('--stage',choices=['time','all'],required=True); args=p.parse_args()
    results=[]
    def check(label,condition):
        results.append((label,bool(condition)))
    x=load_safe(); cg=pd.read_csv(TABLES/'country_group.csv',keep_default_na=False)
    check('输入唯一且匹配 19,694 部',len(x)==19694 and x.id.is_unique)
    check('归属一片一行，缺国家样本保留',len(cg)==len(x) and cg.id.is_unique and (cg.rule=='none').sum()==20)
    check('合并地区与合拍规则边界', all(assign(raw,lang)[1:5]==expected for raw,lang,expected in [
        ('CN|HK','zh',(2,1,'ZH','region_merged')), ('RU|SU','ru',(2,1,'RU','region_merged')),
        ('US|GB','en',(2,1,'US','lang_primary')), ('GB|FR','en',(2,1,'GB','lang_unique')),
        ('MX|ES','es',(2,1,'AMBIG','ambig')), ('GB|FR','xx',(2,1,'AMBIG','ambig')),
        (np.nan,'en',(0,0,'NONE','none'))]))
    joined=x.merge(cg[['id','country_main','rule','n_countries_raw','is_coprod']],on='id',validate='one_to_one')
    check('合拍标记保留原始国家数', (joined.is_coprod == (joined.n_countries_raw>1).astype(int)).all())
    y=pd.read_csv(TABLES/'time_yearly.csv'); d=pd.read_csv(TABLES/'time_decade.csv'); old=pd.read_csv(ROOT/'data/yearly.csv'); z=y.merge(old,on='year',validate='one_to_one')
    check('逐年样本数一致',len(z)==76 and (z.n_total==z.n).all())
    check('逐年中位数与公共表按原表精度一致',all(((z[f'{m}_median']-z[c]).abs() <= tol).all() for m,c,tol in [('mean_v','med_v',.00010001),('mean_s','med_s',.00010001),('colorful','med_colorful',.0050001)]))
    check('年代样本总数与窗口端点',d.n_total.sum()==len(x) and y.n_window.notna().sum()==72 and y.loc[y.year.isin([1950,1951,2024,2025]),'n_window'].isna().all())
    check('逐年及年代统计来自对应电影', all(int(r.n_total)==int((x.year==r.year).sum()) and all(np.isclose(getattr(r,f'{m}_mean'),x.loc[x.year==r.year,m].mean()) for m in METRICS) for r in y.itertuples()) and all(int(r.n_total)==int((x.decade==r.decade).sum()) and all(np.isclose(getattr(r,f'{m}_median'),x.loc[x.decade==r.decade,m].median()) for m in METRICS) for r in d.itertuples()))
    check('完整五年窗口从逐片记录计算', all(int(r.n_window)==len(x[x.year.between(r.year-2,r.year+2)]) and all(np.isclose(getattr(r,f'{m}_window_median'),x.loc[x.year.between(r.year-2,r.year+2),m].median()) for m in METRICS) for r in y.dropna(subset=['n_window']).itertuples()))
    hs=pd.read_csv(TABLES/'hue_summary.csv'); ht=hs[hs.dimension=='time']; cols=[f'h{i}' for i in range(12)]
    check('时间色相有效样本及比例',len(ht)==8 and (ht.n_hue<=ht.n_total).all() and np.allclose(ht[cols].sum(axis=1),1))
    def check_hue(source, row):
        raw=source[cols].to_numpy(dtype=float)
        valid=np.isfinite(raw).all(axis=1) & (raw>=0).all(axis=1) & (raw.sum(axis=1)>0) & (source.sat_frac.to_numpy()>=.1)
        v=raw[valid]; avg=(v/v.sum(axis=1,keepdims=True)).mean(axis=0)
        return row.n_total==len(source) and row.n_hue==len(v) and np.allclose(avg,np.array([getattr(row,c) for c in cols]))
    check('时间色相按逐片归一等权平均', all(check_hue(x[x.decade==int(r.group)],r) for r in ht.itertuples()))
    ct=pd.read_csv(TABLES/'contrasts.csv'); check('时间差值完整',len(ct[ct.dimension=='time'])==6)
    for row in ct[ct.dimension=='time'].itertuples():
        a=x[x.decade==int(row.group_a)]; b=x[x.decade==int(row.group_b)]; calc=contrast(a,b,row.metric)
        check(f'时间差值及区间可复现：{row.group_a}-{row.group_b} {row.metric}', all(np.isclose(getattr(row,k),calc[k]) for k in ['n_a','n_b','mean_difference','ci_low','ci_high']))
    for f in ['figures/fig_q2_trend.png','outputs/c/ppt/fig_q2_hue.png','outputs/c/ppt/fig_q2_metrics.png']:
        check(f+' 存在', (ROOT/f).exists())
    if (ROOT/'figures/fig_q2_trend.png').exists(): check('时间报告图 300 dpi',abs(Image.open(ROOT/'figures/fig_q2_trend.png').info['dpi'][0]-300)<1)
    if args.stage=='all':
        s=pd.read_csv(TABLES/'country_summary.csv'); hc=hs[hs.dimension=='country']; recent=cg[cg.year.between(2001,2025)]
        check('七组样本量与归属一致',s.country_main.tolist()==GROUPS and all(int(s.set_index('country_main').loc[g,'n_total'])==int((recent.country_main==g).sum()) for g in GROUPS))
        subset=joined[joined.year.between(2001,2025) & joined.country_main.isin(GROUPS)]
        check('国家组均值及有效样本数来自对应电影', all(all(int(getattr(r,f'{m}_n_valid'))==subset.loc[subset.country_main==r.country_main,m].notna().sum() and np.isclose(getattr(r,f'{m}_mean'),subset.loc[subset.country_main==r.country_main,m].mean()) for m in METRICS) for r in s.itertuples()))
        check('国家色相比例',len(hc)==7 and np.allclose(hc[cols].sum(axis=1),1))
        check('国家色相按逐片归一等权平均', all(check_hue(subset[subset.country_main==r.group],r) for r in hc.itertuples()))
        check('国家预定对比完整',len(ct[ct.dimension=='country'])==18)
        for row in ct[ct.dimension=='country'].itertuples():
            calc=contrast(subset[subset.country_main==row.group_a],subset[subset.country_main==row.group_b],row.metric)
            check(f'国家差值及区间可复现：{row.group_a}-{row.group_b} {row.metric}', all(np.isclose(getattr(row,k),calc[k]) for k in ['n_a','n_b','mean_difference','ci_low','ci_high']))
        support=pd.read_csv(TABLES/'sample_support.csv')
        check('低样本国家年代格保留并标记', (support.low_n==(support.n<30)).all() and all(int(r.n)==int(((recent.country_main==r.country_main)&(recent.decade==r.decade)).sum()) for r in support.itertuples()))
        for f in ['figures/fig_q4_country.png','outputs/c/ppt/fig_q4_hue.png','outputs/c/ppt/fig_q4_metrics.png']:
            check(f+' 存在',(ROOT/f).exists())
        if (ROOT/'figures/fig_q4_country.png').exists(): check('国家报告图 300 dpi',abs(Image.open(ROOT/'figures/fig_q4_country.png').info['dpi'][0]-300)<1)
    for name in (['fig_q2_hue.png','fig_q2_metrics.png'] + (['fig_q4_hue.png','fig_q4_metrics.png'] if args.stage=='all' else [])):
        path=OUT/'ppt'/name
        if path.exists():
            w,h=Image.open(path).size; check(name+' 为 16:9',w*9==h*16)
    palette_path=TABLES/'palette_summary.csv'
    if palette_path.exists():
        palette=pd.read_csv(palette_path,dtype={'group':str})
        check('配色图覆盖八年代与七组',palette.loc[palette.dimension=='time','group'].nunique()==8 and set(palette.loc[palette.dimension=='country','group'])==set(GROUPS))
        check('配色汇总权重及有效样本数',np.allclose(palette.groupby(['dimension','group']).share.sum(),1) and (palette.n_palette+palette.n_excluded_palette==palette.n_total).all())
        for f in ['fig_q2_palettes.png','fig_q4_palettes.png']:
            path=ROOT/'figures'/f
            check(f+' 存在且为 300 dpi',path.exists() and abs(Image.open(path).info['dpi'][0]-300)<1)
    lines=['# C 阶段验收报告','',f'阶段：{args.stage}','','逐项自动检查：','']+[f"- [{'x' if ok else ' '}] {label}" for label,ok in results]
    lines+=['','说明：丰富度上游年度表仅保留两位小数，使用 ±0.005 核对；明度和饱和度使用 0.0001。','自动检查不替代图面目视检查或跨团队模板核对。']
    (OUT/'reports').mkdir(exist_ok=True)
    (OUT/'reports'/'validation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines));
    if not all(ok for _,ok in results): raise SystemExit(1)
if __name__=='__main__': main()
