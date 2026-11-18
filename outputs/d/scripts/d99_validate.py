"""成员 D 自动化验收脚本：全面核验 docs/报告.md、docs/报告.docx、docs/汇报.pptx、docs/汇报.md 与只读边界。"""
from datetime import datetime
from pathlib import Path
import re
import subprocess
from PIL import Image
from docx import Document
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = Path(__file__).resolve().parents[3]
REPORT_MD = ROOT / "docs" / "报告.md"
REPORT_DOCX = ROOT / "docs" / "报告.docx"
PPTX_PATH = ROOT / "docs" / "汇报.pptx"
PPT_MD = ROOT / "docs" / "汇报.md"
PREVIEW_DIR = ROOT / "outputs" / "d" / "slide_previews"
OUT_REPORT = ROOT / "outputs" / "d" / "validation_report.md"


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    # 1. 核心交付文件存在性与非空核验
    import hashlib
    def sha256_of(fp: Path) -> str:
        return hashlib.sha256(fp.read_bytes()).hexdigest()

    for label, p in [
        ("Markdown 统稿报告 docs/报告.md", REPORT_MD),
        ("Word 出版级报告 docs/报告.docx", REPORT_DOCX),
        ("12 页宽屏演示文稿 docs/汇报.pptx", PPTX_PATH),
        ("配套演讲稿与答辩预案 docs/汇报.md", PPT_MD),
    ]:
        exists = p.is_file() and p.stat().st_size > 2048
        sz_kb = p.stat().st_size / 1024.0 if p.is_file() else 0.0
        add_check(f"文件存在且非空：{label}", exists, f"size = {sz_kb:.1f} KB")

    d_pptx = ROOT / "outputs" / "d" / "汇报.pptx"
    d_docx = ROOT / "outputs" / "d" / "报告.docx"
    outer_pptx = ROOT.parent / "汇报.pptx"
    outer_docx = ROOT.parent / "报告.docx"
    sync_pptx_ok = d_pptx.is_file() and outer_pptx.is_file() and sha256_of(PPTX_PATH) == sha256_of(d_pptx) == sha256_of(outer_pptx)
    sync_docx_ok = d_docx.is_file() and outer_docx.is_file() and sha256_of(REPORT_DOCX) == sha256_of(d_docx) == sha256_of(outer_docx)
    add_check("汇报.pptx 已同步至 outputs/d/ 与外层工作区且字节完全一致", sync_pptx_ok, f"SHA-256 前 8 位 = {sha256_of(PPTX_PATH)[:8]}")
    add_check("报告.docx 已同步至 outputs/d/ 与外层工作区且字节完全一致", sync_docx_ok, f"SHA-256 前 8 位 = {sha256_of(REPORT_DOCX)[:8]}")

    # 2. docs/报告.md 结构、图片引用与关键数值一致性核验
    md_text = REPORT_MD.read_text(encoding="utf-8")
    h2_titles = re.findall(r"^##\s+(.*)$", md_text, flags=re.MULTILINE)
    expected_sections = ["摘要", "1. 研究问题", "2. 数据采集", "3. 特征工程", "4. 结构维度", "5. 时间维度", "6. 效用维度", "7. 空间维度", "8. 讨论与局限", "9. 附录"]
    sec_ok = all(any(h.startswith(es) for h in h2_titles) for es in expected_sections)
    add_check("报告章节完整性（摘要 + 正文 1–8 节 + 第 9 节附录）", sec_ok, f"共检测到 {len(h2_titles)} 个二级章节")

    md_imgs = re.findall(r"^!\[([^\]]*)\]\(([^)]+)\)$", md_text, flags=re.MULTILINE)
    missing_imgs = [rel for _, rel in md_imgs if not (REPORT_MD.parent / rel).resolve().is_file()]
    add_check("报告全部相对路径图片存在（共 13 幅）", len(md_imgs) == 13 and len(missing_imgs) == 0, f"引用 {len(md_imgs)} 幅，缺失 {len(missing_imgs)} 幅")

    # 跨模块核心实证数值锚点核对（A + B + C 一致性）
    required_numbers = [
        ("样本池 19,700 部", "19,700"),
        ("有效海报 19,694 张", "19,694"),
        ("色相有效 19,072 部", "19,072"),
        ("B 爱情−恐怖明度差 +0.1990", "+0.1990"),
        ("B 无监督聚类 ARI 0.9913", "0.9913"),
        ("C 2010s−1950s 明度差 −0.0705", "0.0705"),
        ("C 2020–2025 饱和度回升 +0.0424", "+0.0424"),
        ("A 明度与均分相关 +0.047", "+0.047"),
        ("C 2001–2025 七组总样本 10,115", "10,115"),
        ("C 韩国组相对美国饱和度差 −0.1032", "0.1032"),
    ]
    for desc, token in required_numbers:
        add_check(f"报告跨组核心数值对齐：{desc}", token in md_text, f"检索锚点 `{token}`")

    # 3. docs/报告.docx 物理结构与零 LaTeX 符号残留核验
    doc = Document(str(REPORT_DOCX))
    add_check("Word 报告内嵌高清图像数量 = 13", len(doc.inline_shapes) == 13, f"inline_shapes = {len(doc.inline_shapes)}")
    add_check("Word 报告学术三线表数量 = 6", len(doc.tables) == 6, f"tables = {len(doc.tables)}")

    tex_leaks = []
    for idx, p in enumerate(doc.paragraphs):
        if "$" in p.text or "\\" in p.text:
            tex_leaks.append(f"P{idx}: {p.text[:40]}")
    for ti, t in enumerate(doc.tables):
        for ri, r in enumerate(t.rows):
            for ci, c in enumerate(r.cells):
                if "$" in c.text or "\\" in c.text:
                    tex_leaks.append(f"T{ti}R{ri}C{ci}: {c.text[:40]}")
    add_check("Word 报告零裸露 LaTeX 定界符 ($ / \\)", len(tex_leaks) == 0, f"残留数 = {len(tex_leaks)}")

    # 4. docs/汇报.pptx 幻灯片页数、16:9 尺寸、图片宽高比零变形与备注核验
    prs = Presentation(str(PPTX_PATH))
    w_in = prs.slide_width.inches
    h_in = prs.slide_height.inches
    add_check("PPT 页数严格等于 12 页", len(prs.slides) == 12, f"slides = {len(prs.slides)}")
    add_check("PPT 画布为标准 16:9 宽屏 (13.333 × 7.500 in)", abs(w_in - 13.333) < 0.01 and abs(h_in - 7.5) < 0.01, f"{w_in:.3f} × {h_in:.3f} in")

    pic_count = 0
    distorted = 0
    notes_ok = 0
    bounds_violations = 0
    for si, slide in enumerate(prs.slides, start=1):
        if slide.has_notes_slide and len(slide.notes_slide.notes_text_frame.text.strip()) > 30:
            notes_ok += 1
        for shp in slide.shapes:
            # 检查形状是否越出画布边界（允许 0.05 in 容差）
            left_in = shp.left.inches
            top_in = shp.top.inches
            right_in = left_in + shp.width.inches
            bot_in = top_in + shp.height.inches
            if left_in < -0.05 or top_in < -0.05 or right_in > w_in + 0.05 or bot_in > h_in + 0.05:
                bounds_violations += 1
            if shp.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pic_count += 1
                with Image.open(shp.image.blob if hasattr(shp.image, "blob") else "") if False else Image.frombytes("RGB", (1, 1), b"\x00\x00\x00"):
                    pass
                px_w, px_h = shp.image.size
                nat_ratio = px_w / max(px_h, 1)
                shp_ratio = shp.width / max(shp.height, 1)
                if abs(nat_ratio - shp_ratio) / nat_ratio > 0.01:
                    distorted += 1

    add_check("PPT 内嵌图表总数（13 幅）且全部保持原始宽高比（变形率 < 1%）", pic_count == 13 and distorted == 0, f"图片 {pic_count} 幅，变形 {distorted} 幅")
    add_check("PPT 全部元素严格位于 16:9 画布边界内（零越界裁切）", bounds_violations == 0, f"越界形状数 = {bounds_violations}")
    add_check("PPT 12 页全部内嵌完整演讲者备注（Speaker Notes）", notes_ok == 12, f"含备注页数 = {notes_ok} / 12")

    # 5. PowerPoint 渲染高清预览图完整性核验
    previews = sorted(PREVIEW_DIR.glob("slide_*.png"))
    prev_dims_ok = True
    for pv in previews:
        with Image.open(pv) as im:
            if im.size != (1920, 1080):
                prev_dims_ok = False
    add_check("PPT 12 页 1920×1080 渲染预览图齐全", len(previews) == 12 and prev_dims_ok, f"导出 {len(previews)} 张 1920×1080 PNG")

    # 6. 只读目录防污染核验（data/、scripts/、outputs/a/、outputs/c/ 零修改）
    git_res = subprocess.run(
        ["git", "status", "--porcelain", "--", "data/", "scripts/", "outputs/a/", "outputs/c/", "figures/c/", "figures/fig_q3_score.png"],
        cwd=str(ROOT), capture_output=True, text=True, check=True,
    )
    dirty_lines = [ln for ln in git_res.stdout.splitlines() if ln.strip()]
    add_check("只读保护区（data/ · scripts/ · A/C 产物）零改动", len(dirty_lines) == 0, f"变更行数 = {len(dirty_lines)}")

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    rep = [
        "# 成员 D 统稿与演示交付自动化核验报告",
        "",
        f"- **生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **核验结果**：**{passed} / {total} 项全部通过**" if passed == total else f"- **核验结果**：**{passed} / {total} 项通过（存在失败项）**",
        "",
        "| 序号 | 核验项目 | 状态 | 观测详情 |",
        "| :---: | --- | :---: | --- |",
    ]
    for idx, (name, ok, detail) in enumerate(checks, start=1):
        rep.append(f"| {idx} | {name} | {'PASS' if ok else 'FAIL'} | {detail} |")

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"成员 D 核验完成：{passed} / {total} 项通过 -> {OUT_REPORT}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
