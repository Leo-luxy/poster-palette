# 海报会说话——电影海报配色的类型结构、时间演变、地区差异与口碑效用实证研究

> 数据分析实践 · 课程大作业

**一句话结论**：基于 TMDB 1950—2025 年 **19,700 部**电影与 **19,694 张**原语言版海报，从**类型结构、时间演变、地区空间、口碑效用**四个维度实证揭示——**海报配色是帮观众快速识别题材的「分类路由信号」，而非反映影片好坏的「质量信号」**。

---

## 核心成果速览（全部已完成并通过自动核验）

| 维度 | 核心方法与抗偏误设计 | 关键实证发现 | 核心图件与报告入口 |
| --- | --- | --- | --- |
| **数据基线 (A)** | 每年取票数**前 2.6%** 动态分位门槛 + **原语言版海报**替换 + 裁底部 12% + 近灰像素掩膜 ($S \ge 0.20$) 与色相闸门 ($\text{sat\_frac} \ge 0.10$) | 八个年代入库率拉平至 **2.61%–3.06%**（1950s 由 261 扩至 868 部）；替换 **7,724 张**中文化海报，原语言覆盖率达 **98.6%** | [`data/quality_report.md`](data/quality_report.md)<br>[`docs/数据字典.md`](docs/数据字典.md) |
| **① 结构 (B)** | 九大类型多标签电影级联合 Bootstrap + 屏蔽 $0^\circ\text{–}60^\circ$ 肤色区重归一 + `Conic_5D` 圆锥色度无监督 K-Means ($k=4$) | **明度是区分类型头号指标**（互斥 $\eta^2_H = 0.2193$，爱情较恐怖亮 **+0.1990**）；识别出**明亮浅调 (28.6%)、浓烈暖调 (25.9%)、青蓝冷调 (19.4%)、深暗低彩 (26.0%)** 四套跨题材共享模板（ARI = **0.9913**） | [`figures/b/fig_q1_hue.png`](figures/b/fig_q1_hue.png)<br>[`figures/b/fig_q1_cluster.png`](figures/b/fig_q1_cluster.png)<br>[`outputs/b/README.md`](outputs/b/README.md) |
| **② 时间 (C)** | 1950–2025 五年居中滑动窗口 + 14 类无序主辅色共现与 $\Delta E_{76}$ + $30^\circ$ 余弦冷暖投影 + 空间构图中心 | 2010s 较 1950s 明度 **−0.0705**、丰富度 **−16.88**、主辅色差 **−14.72**；**1975–1985 年是暖亮向冷暗跃迁的分水岭**；**2020–2025 饱和度逆势反弹 +0.0424**，中心聚光 **+0.0289** | [`figures/c/fig_q2_trend.png`](figures/c/fig_q2_trend.png)<br>[`figures/c/advanced/v3-20261118/fig_q2_q4_warmth.png`](figures/c/advanced/v3-20261118/fig_q2_q4_warmth.png)<br>[`outputs/c/reports/时间结论.md`](outputs/c/reports/时间结论.md) |
| **③ 空间 (C)** | 2001–2025 原语言锚定合拍归属（七组 10,115 部）+ 七组 $1/7$ 等权参照 + $64\times 45$ 像素级空间残差 + 偏差校正平方距离 $D^2$ | 法(**+0.0598**)/意(**+0.0715**)全幅通透偏亮，日青蓝居首(**33.0%**)，华语外暗内亮(`center_edge_v` **+0.0383**)，韩国在明度(**−0.0772**)/饱和度(**−0.1032**)/丰富度上全线最低；三期 21 对距离 **1.111 → 0.988 → 0.354** 快速趋近 | [`figures/c/fig_q4_country.png`](figures/c/fig_q4_country.png)<br>[`figures/c/advanced/v3-20261118/fig_q4_spatial.png`](figures/c/advanced/v3-20261118/fig_q4_spatial.png)<br>[`figures/c/advanced/v3-20261118/fig_q4_convergence.png`](figures/c/advanced/v3-20261118/fig_q4_convergence.png) |
| **④ 效用 (A)** | 19,592 部有效评分影片全库与分八大类型相关分析 + 大样本 $p$ 值与实质效应量辨析 | 明度 ($r = \mathbf{+0.047}$)、饱和度 ($\mathbf{-0.052}$)、丰富度 ($\mathbf{-0.045}$) 及各类型 $|r|$ **全部落在 0.08 以内**（$R^2 < 0.3\%$），配色不预测评分 | [`figures/fig_q3_score.png`](figures/fig_q3_score.png)<br>[`data/fig3_stats.csv`](data/fig3_stats.csv) |
| **成稿交付 (D)** | 全组统稿、A4 Word 三线表与 300-DPI 内嵌图自动编译、12 页 16:9 宽屏 PPT 与渲染预览 | 正式课程报告、全组故事综合报告（含 27 幅图）、12 页宽屏演示文稿及逐页演讲稿／答辩预案全部就绪 | [` outputs/d/综合报告.md`](outputs/d/综合报告.md)<br>[`docs/报告.md`](docs/报告.md) · [`docs/报告.docx`](docs/报告.docx)<br>[`docs/汇报.pptx`](docs/汇报.pptx) · [`docs/汇报.md`](docs/汇报.md) |

---

## 仓库目录结构

一条完整落地、每一层产物均可直接读取而无需重跑上游的流水线：

```text
poster-palette/
├── README.md                    仓库总览（本文件）
├── data/                        【只读】v2 公共数据资产（pre-commit + CI 保护）
│   ├── movies.csv               19,700 部电影元数据（1950–2025，每年票数前 2.6%）
│   ├── color_features.csv       19,694 行 × 25 列海报配色特征（HSV / 12 扇区 / 丰富度 / 3 主色）
│   ├── movie_details.csv        19,700 行逐片详情（制片国家 130 个 / 预算 / 票房 / 片长 / 系列）
│   ├── yearly.csv               76 行年度聚合表（全类型）
│   ├── yearly_by_genre.csv      1,411 行年度 × 类型聚合表
│   ├── fig3_stats.csv           图 3 配色与评分分类型相关统计
│   ├── quality_report.md        v2 数据采集质量体检报告
│   └── posters/                 19,694 张原语言版海报原图（342×512，共 911 MB）
├── figures/                     定稿图表发布目录（全部 300 dpi，中文标签）
│   ├── fig_q1_hue.png           图 1 主图副本
│   ├── fig_q3_score.png         图 3：配色 × 观众评分（A）
│   ├── b/                       图 1 系列：类型色相与指标、预定对比与肤色屏蔽、k=4 色型聚类、抽象色卡（B）
│   └── c/                       图 2 & 图 4 系列：基线趋势/跨国对比/色卡 + advanced/v3-20261118/ 12 张深度图（C）
├── docs/                        正式提交文档与团队规范
│   ├── 报告.md / 报告.docx       课程报告定稿（Markdown 源码与 A4 出版级 Word 文档）
│   ├── 汇报.pptx / 汇报.md       12 页 16:9 宽屏演示文稿与配套逐页讲稿、答辩 Q&A 预案
│   ├── 数据字典.md               字段定义、计算公式、采样与去本地化口径、常见坑
│   ├── 交接文档.md               各模块绘图规范与验收标准
│   └── 协作流程.md               Git 协作与只读保护说明
├── scripts/                     公共基础脚本（采集、体检、特征提取、年度聚合、图 3、common.py）
├── probe/                       v2 动态分位补片、原语言海报挑选与下载、前后对比探测脚本（A）
└── outputs/                     各成员工作区（代码、统计表、验证报告、16:9 PPT 图面）
    ├── a/                       v1 备份、年代分位门槛表、原语言换图计划与特征扰动图
    ├── b/                       结构维度（类型对比 + Conic_5D 无监督聚类）脚本、表、报告与 36 项验收
    ├── c/                       时间与空间维度（基线 + v3-20261118 增量）脚本、表、报告与 70+98 项验收
    └── d/                       统稿编译脚本、综合报告（27 图完整叙事版）、PPT 预览图与 28 项验收
```

---

## 数据资产（v2 定稿口径）

| 文件 | 规模 | 核心说明 |
| --- | --- | --- |
| `data/movies.csv` | 19,700 部 | 1950–2025 年，按「每年投票人数前 2.6%」动态门槛入库（1950s 门槛 48–72 票，2010s 144–268 票） |
| `data/color_features.csv` | 19,694 行 | 裁除底部 12% 演职员区、缩放至 120×160；含 `mean_v`、`mean_s`、`v_std`、`colorful`、`sat_frac` 及 $S \ge 0.20$ 掩膜下的 `hue`、`h0..h11`、`dom1..3`、`ds1..3` |
| `data/movie_details.csv` | 19,700 行 | 19,674 部含制片国家记录（覆盖 130 个国家／地区：美国 12,135、法国 2,730、英国 2,722、意大利 1,592、德国 1,166、加拿大 1,013、日本 921、西班牙 604、香港 376、中国大陆 291、韩国 280 等） |
| `data/yearly*.csv` | 76 + 1,411 行 | 逐年与逐年×类型聚合表（所有年份 $n \ge 30$） |
| `data/posters/` | 19,694 张 | $342 \times 512$ JPG，共 911 MB；**原语言版覆盖率 98.6%**（替换了 v1 中 7,724 张中文化海报） |

---

## 分工、完成状态与自动化核验

全组采用「`data/` 只读 + 分目录无冲突直推 `main` + 独立自动化验收脚本」的工程模式，**总计 232 项自动化断言 100% 通过**：

| 成员 | 负责模块 | 状态 | 核心交付路径 | 自动化核验命令与结果 |
| --- | --- | :---: | --- | --- |
| **A** | 数据工程与口碑效用 (Q3) | ✅ 已完成 | `data/`、`scripts/`、`probe/`、`outputs/a/`、`figures/fig_q3_score.png` | `python scripts/02_check.py`<br>19,700 部主键唯一，海报覆盖率 100% |
| **B** | 类型结构与无监督聚类 (Q1) | ✅ 已完成 | `outputs/b/`、`figures/b/fig_q1_*.png`、`figures/fig_q1_hue.png` | `python outputs/b/scripts/b99_validate.py`<br>[**36 / 36 项通过**](outputs/b/reports/validation_report.md) |
| **C** | 时间演变与跨国对比 (Q2 & Q4) | ✅ 已完成 | `outputs/c/`、`figures/c/fig_q2_*.png`、`figures/c/fig_q4_*.png`、`figures/c/advanced/v3-20261118/` | `python outputs/c/scripts/c99_validate.py --stage all`<br>`python outputs/c/scripts/c99_validate.py --stage advanced --run-id v3-20261118`<br>[**基线 70/70 + 增量 98/98 项通过**](outputs/c/tables/advanced/v3-20261118/validation_report.md) |
| **D** | 报告统稿、Word 排版与 12 页 PPT | ✅ 已完成 | `docs/报告.md`、`docs/报告.docx`、`docs/汇报.pptx`、`docs/汇报.md`、`outputs/d/综合报告.md` | `python outputs/d/scripts/d99_validate.py`<br>[**28 / 28 项通过**](outputs/d/validation_report.md) |

---

## 快速阅读与复现指南

### 1. 不跑代码，直接看成果
- **想看全组完整故事与全部 27 幅图表解读**：打开 [`outputs/d/综合报告.md`](outputs/d/综合报告.md)
- **想看正式提交版课程报告与 PPT**：打开 [`docs/报告.docx`](docs/报告.docx)（或 [`docs/报告.md`](docs/报告.md)）与 [`docs/汇报.pptx`](docs/汇报.pptx)（配套讲稿见 [`docs/汇报.md`](docs/汇报.md)，单页高清预览见 `outputs/d/slide_previews/`）
- **想看各分模块的方法细节与统计表**：
  - B 组（类型与色型聚类）：[`outputs/b/项目实现与结果解读.md`](outputs/b/项目实现与结果解读.md)
  - C 组（时间与国家分析）：[`outputs/c/C组工作总结与交付指南.md`](outputs/c/C组工作总结与交付指南.md)、[`outputs/c/项目实现与结果解读.md`](outputs/c/项目实现与结果解读.md)
  - 数据口径与字段字典：[`docs/数据字典.md`](docs/数据字典.md)

### 2. 本地一键重跑与核验（无需联网，无需 API Key）

在仓库根目录下执行：

```bash
# 1) 验证或重跑 B 组（类型对比 + 无监督色型聚类）
python outputs/b/scripts/b99_validate.py

# 2) 验证或重跑 C 组（时间趋势 + 跨国差异 + v3-20261118 增量分析）
python outputs/c/scripts/c99_validate.py --stage all
python outputs/c/scripts/c99_validate.py --stage advanced --run-id v3-20261118

# 3) 重新编译 D 组 Word 报告、12 页 PPT 并运行跨模块一致性核验
python outputs/d/scripts/d01_build_report_docx.py
python outputs/d/scripts/d02_build_ppt.py
python outputs/d/scripts/d99_validate.py
```

---

## 数据来源与版权声明

- 数据采集自 TMDB API，上映日期范围为 `1950-01-01` 至 `2025-12-31`，v1 采集于 **2026-11-02**，v2 动态分位补片与原语言海报替换完成于 **2026-11-03**。
- 海报图像版权归各出品与发行片方所有，本仓库仅用于课程作业的学术研究与课堂展示，不做商业分发。
- 仓库包含全部 19,694 张海报原图（约 911 MB），完整克隆体积较大；若仅查阅代码、统计表与定稿文档可使用浅克隆：

```bash
git clone --depth 1 https://github.com/Leo-luxy/poster-palette.git
```
