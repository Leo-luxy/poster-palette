# C 阶段验收报告

阶段：all

逐项自动检查：

- [x] 输入唯一且匹配 19,694 部
- [x] 归属一片一行，缺国家样本保留
- [x] 合并地区与合拍规则边界
- [x] 合拍标记保留原始国家数
- [x] 逐年样本数一致
- [x] 逐年中位数与公共表按原表精度一致
- [x] 年代样本总数与窗口端点
- [x] 逐年及年代统计来自对应电影
- [x] 完整五年窗口从逐片记录计算
- [x] 时间色相有效样本及比例
- [x] 时间色相按逐片归一等权平均
- [x] 时间差值完整
- [x] 时间差值及区间可复现：2010-1950 mean_v
- [x] 时间差值及区间可复现：2010-1950 mean_s
- [x] 时间差值及区间可复现：2010-1950 colorful
- [x] 时间差值及区间可复现：2020-2010 mean_v
- [x] 时间差值及区间可复现：2020-2010 mean_s
- [x] 时间差值及区间可复现：2020-2010 colorful
- [x] figures/fig_q2_trend.png 存在
- [x] outputs/c/ppt/fig_q2_hue.png 存在
- [x] outputs/c/ppt/fig_q2_metrics.png 存在
- [x] 时间报告图 300 dpi
- [x] 七组样本量与归属一致
- [x] 国家组均值及有效样本数来自对应电影
- [x] 国家色相比例
- [x] 国家色相按逐片归一等权平均
- [x] 国家预定对比完整
- [x] 国家差值及区间可复现：GB-US mean_v
- [x] 国家差值及区间可复现：GB-US mean_s
- [x] 国家差值及区间可复现：GB-US colorful
- [x] 国家差值及区间可复现：FR-US mean_v
- [x] 国家差值及区间可复现：FR-US mean_s
- [x] 国家差值及区间可复现：FR-US colorful
- [x] 国家差值及区间可复现：IT-US mean_v
- [x] 国家差值及区间可复现：IT-US mean_s
- [x] 国家差值及区间可复现：IT-US colorful
- [x] 国家差值及区间可复现：JP-US mean_v
- [x] 国家差值及区间可复现：JP-US mean_s
- [x] 国家差值及区间可复现：JP-US colorful
- [x] 国家差值及区间可复现：ZH-US mean_v
- [x] 国家差值及区间可复现：ZH-US mean_s
- [x] 国家差值及区间可复现：ZH-US colorful
- [x] 国家差值及区间可复现：KR-US mean_v
- [x] 国家差值及区间可复现：KR-US mean_s
- [x] 国家差值及区间可复现：KR-US colorful
- [x] 低样本国家年代格保留并标记
- [x] figures/fig_q4_country.png 存在
- [x] outputs/c/ppt/fig_q4_hue.png 存在
- [x] outputs/c/ppt/fig_q4_metrics.png 存在
- [x] 国家报告图 300 dpi
- [x] fig_q2_hue.png 为 16:9
- [x] fig_q2_metrics.png 为 16:9
- [x] fig_q4_hue.png 为 16:9
- [x] fig_q4_metrics.png 为 16:9
- [x] 配色图覆盖八年代与七组
- [x] 配色汇总权重及有效样本数
- [x] fig_q2_palettes.png 存在且为 300 dpi
- [x] fig_q4_palettes.png 存在且为 300 dpi

说明：丰富度上游年度表仅保留两位小数，使用 ±0.005 核对；明度和饱和度使用 0.0001。
自动检查不替代图面目视检查或跨团队模板核对。
