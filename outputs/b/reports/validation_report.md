# B 阶段自动验收报告

逐项自动检查：

- [x] 输入唯一且匹配 19,694 部
- [x] 色相有效样本 sat_frac≥0.10 为 19,072 部
- [x] genre_summary 覆盖 9 大类型与全库 ALL
- [x] 各类型总片数与直接筛选完全一致
- [x] 各类型 12 扇区色相占比和为 1
- [x] 各类型色相按逐片归一等权平均且与 common.hue_share 一致
- [x] genre_contrasts 全部 72 项差值与 95% CI 完整有效且满足 ci_low < diff < ci_high
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：爱情-恐怖 mean_v
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：爱情-恐怖 mean_s
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：爱情-恐怖 colorful
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：爱情-科幻 mean_v
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：爱情-科幻 mean_s
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：爱情-科幻 colorful
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：科幻-恐怖 mean_v
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：科幻-恐怖 mean_s
- [x] 预定对比差值及联合 Bootstrap 95% CI 可复现：科幻-恐怖 colorful
- [x] 聚类基准表全部基于 N=19,072 统一口径
- [x] 聚类分配表唯一覆盖 19,072 部且四簇总和严格等于 19,072
- [x] 四类色型占比和为 1 且最小簇占比 > 15%
- [x] 各类型色型构成每行和为 1
- [x] 各年代色型构成每行和为 1 且样本总和为 19,072
- [x] 典型海报覆盖 4 类色型与 9 类电影且无重复影片
- [x] 示例海报文件存在、SHA-256 指纹一致且 7 色比例和为 1
- [x] figures/fig_q1_hue.png 存在且为 300 dpi
- [x] figures/b/fig_q1_hue.png 存在且为 300 dpi
- [x] figures/b/fig_q1_comparisons.png 存在且为 300 dpi
- [x] figures/b/fig_q1_cluster.png 存在且为 300 dpi
- [x] figures/b/fig_q1_palettes.png 存在且为 300 dpi
- [x] 根目录 figures/fig_q1_hue.png 与 figures/b/fig_q1_hue.png 完全同步
- [x] outputs/b/ppt/fig_q1_genre_hue.png 存在
- [x] outputs/b/ppt/fig_q1_genre_hue.png 严格满足 16:9 像素比 (2400×1350)
- [x] outputs/b/ppt/fig_q1_genre_metrics.png 存在
- [x] outputs/b/ppt/fig_q1_genre_metrics.png 严格满足 16:9 像素比 (2400×1350)
- [x] outputs/b/ppt/fig_q1_cluster.png 存在
- [x] outputs/b/ppt/fig_q1_cluster.png 严格满足 16:9 像素比 (2400×1350)
- [x] outputs/b/ppt/fig_q1_palettes.png 存在
- [x] outputs/b/ppt/fig_q1_palettes.png 严格满足 16:9 像素比 (2400×1350)

说明：色相与无监督聚类严格限定 sat_frac ≥ 0.10（N=19,072），连续指标保留全量有效记录（N=19,694）；多标签对比采用电影级联合重采样 Bootstrap（1,000 次）。
