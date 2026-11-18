# D：课程报告统稿、Word 出版排版与 12 页宽屏演示文稿

本目录收纳成员 D 负责的全组统稿构建脚本、12 页 PPT 渲染预览图与自动化验收报告。核心正式交付物位于 `docs/` 目录：

- [`docs/报告.md`](../../docs/报告.md)：九节 + 附录完整课程报告（整合 A 数据与口碑、B 类型与无监督聚类、C 时间与跨国对比全量成果，含 13 幅图表引用与 6 张统计表）。
- [`docs/报告.docx`](../../docs/报告.docx)：由脚本自动编译生成的 A4 出版级 Word 文档（内嵌 13 幅 300-DPI 高清图、6 张学术三线表、Unicode 数学公式美化与页眉页脚页码）。
- [`docs/汇报.pptx`](../../docs/汇报.pptx)：标准 16:9 宽屏（13.333 × 7.5 in）12 页课程汇报演示文稿（严格锁定图片原始宽高比，每页均内嵌完整演讲者备注）。
- [`docs/汇报.md`](../../docs/汇报.md)：配套 12 页幻灯片时间分配表、逐页口头讲稿与高频答辩 Q&A 备询预案。

```text
outputs/d/
├── README.md                 目录入口与一键重编说明
├── 汇报.pptx                 与 docs/汇报.pptx 同步的 12 页 16:9 宽屏演示文稿
├── 汇报.md                   与 docs/汇报.md 同步的逐页口头讲稿与答辩 Q&A 预案
├── 报告.docx                 与 docs/报告.docx 同步的出版级 Word 课程报告
├── 报告.md                   与 docs/报告.md 同步的 Markdown 课程报告源码
├── validation_report.md      28 项自动化质量与跨模块一致性核验报告
├── scripts/
│   ├── d01_build_report_docx.py  由 docs/报告.md 生成并同步 报告.docx
│   ├── d02_build_ppt.py          生成并同步 汇报.pptx 与 汇报.md
│   ├── d03_export_previews.py    调用 PowerPoint 导出 1920×1080 逐页视觉预览
│   └── d99_validate.py           文档、图表宽高比、零 LaTeX 残留及同步核验
└── slide_previews/           slide_01.png .. slide_12.png 高清页面渲染图
```

## 一键重新生成与核验命令

在仓库根目录下依次执行：

```bash
python outputs/d/scripts/d01_build_report_docx.py
python outputs/d/scripts/d02_build_ppt.py
python outputs/d/scripts/d03_export_previews.py
python outputs/d/scripts/d99_validate.py
```
