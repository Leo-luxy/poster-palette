# 数据分析实践 · 大作业

**题目**：海报会说话——四十年电影配色里的类型密码

用 14,662 部电影海报的配色数据，回答三个问题：类型能不能用颜色区分？配色四十年怎么变？颜色能不能预测口碑？

## 现在有什么

| 内容 | 说明 |
| --- | --- |
| `data/movies.csv` | 14,662 部电影元数据（1950–2025，TMDB） |
| `data/color_features.csv` | 14,657 张海报的配色特征（饱和度/明度/色相分布/主色） |
| `data/yearly*.csv` | 年度聚合表，做趋势图直接读 |
| `figures/` | 已完成的图（目前：图 3） |
| `docs/数据字典` | 每个字段怎么算、范围、哪些要过滤 |
| `docs/交接文档` | 五分钟上手 + 每人那张图的画法与验收标准 |
| `02-分工与数据交接` | 谁做什么、交接规矩 |

## 快速开始

```bash
python3 -c "import pandas, numpy, matplotlib, sklearn, scipy; print('环境 OK')"
```

```python
import sys; sys.path.insert(0, 'scripts')
import common

df = common.load()          # 合并两张表，自动加 decade / genres
print(len(df))              # 14657
```

**不需要 API key**，所有数据都已落盘。

## 海报图没有进仓库

`data/posters/`（14,657 张，716 MB）体积太大，且海报版权归片方，不放进 Git。
需要看图请从共享盘取，或按 `data/movies.csv` 里的 `poster_path` 自己下：

```python
url = f"https://image.tmdb.org/t/p/w342{poster_path}"   # 公开图床，不用 key
```

## 数据来源

TMDB API，`vote_count ≥ 200`，1950-01-01 至 2025-12-31，采集于 **2026-11-02**。
数据按 TMDB 条款使用，仅用于课程作业，不再分发。
