# C：海报配色的时间与国家／地区分析

本目录收纳代码、计划、统计表、解读和 PPT 图面。报告图位于仓库的 `figures/`：`fig_q2_trend.png`、`fig_q4_country.png` 是统计组合图；`fig_q2_palettes.png`、`fig_q4_palettes.png` 是年代及国家／地区的抽象色块拼接图。

```text
outputs/c/
├── README.md            目录入口
├── run_manifest.json    输入指纹、运行环境和配置
├── palette_manifest.json 配色图的分类规则
├── scripts/             国家归属、时间与国家分析、绘图和验收代码
├── docs/                原始执行计划、简明说明及协作推送记录
├── reports/             时间与国家结论、复现说明及验收报告
├── tables/              统计结果、归属记录和输入审计表
└── ppt/                 四张 16:9 图面和逐页讲述建议
```

建议从 [时间结论](reports/时间结论.md)、[国家结论](reports/国家结论.md) 和 [PPT 讲述建议](ppt/讲述建议.md) 查看成果；完整数据表在 `tables/`。可复现步骤见 [复现说明](reports/复现说明.md)，检查结果见 [验收报告](reports/validation_report.md)。

`docs/` 中的执行计划保留其制定时的内容，里面的文件路径属于整理前的历史约定；当前目录结构和运行命令以本文件及复现说明为准。
