"""将 docs/报告.md 编译为出版级 A4 Word 文档 docs/报告.docx（含嵌入高清图、三线表、数学符号美化与页码）。"""
from pathlib import Path
import re
from PIL import Image
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[3]
SRC_MD = ROOT / "docs" / "报告.md"
DST_DOCX = ROOT / "docs" / "报告.docx"
COPY_D_DOCX = ROOT / "outputs" / "d" / "报告.docx"
COPY_D_MD = ROOT / "outputs" / "d" / "报告.md"
OUTER_DOCX = ROOT.parent / "报告.docx"

FONT_BODY = "宋体"
FONT_WEST = "Times New Roman"
FONT_HEAD = "微软雅黑"
FONT_CODE = "Consolas"


def clean_tex(s: str) -> str:
    """将 Markdown 中的轻量 LaTeX 数学记号转换为整洁的 Unicode 学术排版字符，杜绝裸露反斜杠。"""
    rep = [
        (r"\\text\{([^}]*)\}", r"\1"),
        (r"\\frac\{([^}]*)\}\{([0-9a-zA-Z]+)\}", r"(\1)/\2"),
        (r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)"),
        (r"\\bigl\[", "["),
        (r"\\bigr\]", "]"),
        (r"\\quad", "    "),
        (r"\\cos", "cos"),
        (r"\\sin", "sin"),
        (r"\\%", "%"),
        (r"\\\{", "{"),
        (r"\\\}", "}"),
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\pm", "±"),
        (r"\\ge", "≥"),
        (r"\\le", "≤"),
        (r"\\equiv", "≡"),
        (r"\\approx", "≈"),
        (r"\\to", "→"),
        (r"\\in", "∈"),
        (r"\\sum_\{i=0\}\^\{11\}", "∑(i=0..11)"),
        (r"\\eta\^2_H", "η²_H"),
        (r"\\rho", "ρ"),
        (r"\\sigma_\{rg\}\^2", "σ_rg²"),
        (r"\\sigma_\{yb\}\^2", "σ_yb²"),
        (r"\\mu_\{rg\}\^2", "μ_rg²"),
        (r"\\mu_\{yb\}\^2", "μ_yb²"),
        (r"n_\{([^}]*)\}", r"n_\1"),
        (r"\\Delta", "Δ"),
        (r"\\sqrt\{([^}]*)\}", r"√(\1)"),
        (r"\\mathbf\{([^}]*)\}", r"\1"),
        (r"\^\\circ", "°"),
        (r"10\^\{-300\}", "10⁻³⁰⁰"),
        (r"10\^\{-36\}", "10⁻³⁶"),
        (r"10\^\{-10\}", "10⁻¹⁰"),
        (r"10\^\{-6\}", "10⁻⁶"),
        (r"10\^\{-5\}", "10⁻⁵"),
        (r"10\^\{-4\}", "10⁻⁴"),
        (r"R\^2", "R²"),
        (r"\\;", " "),
        (r"\\,", " "),
        (r"\\_", "_"),
    ]
    out = s
    for pat, val in rep:
        out = re.sub(pat, val, out)
    # 去除行内 $...$ 定界符，保留内部已转化的数学文本
    out = re.sub(r"\$\$([^$]+)\$\$", r"\1", out)
    out = re.sub(r"\$([^$]+)\$", r"\1", out)
    if "$" in out or "\\" in out:
        raise ValueError(f"未清理干净的 LaTeX 符号残留: {out}")
    return out


def set_run_font(run, east_asia: str = FONT_BODY, west: str = FONT_WEST, size: float = 10.5, bold: bool = False, italic: bool = False, color: tuple[int, int, int] | None = None) -> None:
    run.font.name = west
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), east_asia)
    rfonts.set(qn("w:ascii"), west)
    rfonts.set(qn("w:hAnsi"), west)


def add_rich_runs(p, text: str, size: float = 10.5, base_east: str = FONT_BODY, base_bold: bool = False, color: tuple[int, int, int] = (30, 41, 59)) -> None:
    text = clean_tex(text)
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = p.add_run(tok[2:-2])
            set_run_font(r, east_asia=FONT_HEAD, west=FONT_WEST, size=size, bold=True, color=(15, 23, 42))
        elif tok.startswith("*") and tok.endswith("*"):
            r = p.add_run(tok[1:-1])
            set_run_font(r, east_asia=base_east, west=FONT_WEST, size=size, bold=base_bold, italic=True, color=color)
        elif tok.startswith("`") and tok.endswith("`"):
            r = p.add_run(tok[1:-1])
            set_run_font(r, east_asia=FONT_CODE, west=FONT_CODE, size=size - 0.5, bold=base_bold, color=(30, 58, 95))
        elif tok.startswith("[") and "](" in tok and tok.endswith(")"):
            lbl = tok[1 : tok.index("](")]
            r = p.add_run(lbl)
            set_run_font(r, east_asia=base_east, west=FONT_WEST, size=size, bold=base_bold, color=(29, 111, 165))
        else:
            r = p.add_run(tok)
            set_run_font(r, east_asia=base_east, west=FONT_WEST, size=size, bold=base_bold, color=color)


def set_paragraph_bottom_border(p, color_hex: str = "CBD5E1", sz: str = "6") -> None:
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="{sz}" w:space="4" w:color="{color_hex}"/></w:pBdr>')
    pPr.append(pBdr)


def add_page_number_footer(section) -> None:
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("— 第 ")
    set_run_font(r1, east_asia=FONT_BODY, size=9.0, color=(100, 116, 139))
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    p._p.append(fld)
    r2 = p.add_run(" 页 —")
    set_run_font(r2, east_asia=FONT_BODY, size=9.0, color=(100, 116, 139))

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("数据分析实践 · 海报会说话：19,694 张电影海报配色实证研究")
    set_run_font(hr, east_asia=FONT_HEAD, west=FONT_HEAD, size=8.5, color=(148, 163, 184))


def style_three_line_table(table, alignments: list[str]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="0F172A"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="0F172A"/>'
        '<w:insideH w:val="none"/>'
        '<w:insideV w:val="none"/>'
        '<w:left w:val="none"/>'
        '<w:right w:val="none"/>'
        "</w:tblBorders>"
    )
    tblPr.append(borders)

    for ri, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        if ri == 0:
            trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

        for ci, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            tcPr = cell._tc.get_or_add_tcPr()
            tcMar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                '<w:top w:w="85" w:type="dxa"/>'
                '<w:bottom w:w="85" w:type="dxa"/>'
                '<w:left w:w="95" w:type="dxa"/>'
                '<w:right w:w="95" w:type="dxa"/>'
                "</w:tcMar>"
            )
            tcPr.append(tcMar)
            if ri == 0:
                tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>'))
                tcPr.append(
                    parse_xml(
                        f'<w:tcBorders {nsdecls("w")}>'
                        '<w:top w:val="single" w:sz="12" w:space="0" w:color="0F172A"/>'
                        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="334155"/>'
                        "</w:tcBorders>"
                    )
                )
            elif ri == len(table.rows) - 1:
                tcPr.append(
                    parse_xml(
                        f'<w:tcBorders {nsdecls("w")}>'
                        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="0F172A"/>'
                        "</w:tcBorders>"
                    )
                )

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.18
            al = alignments[ci] if ci < len(alignments) else "left"
            if al == "right":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif al == "center":
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def main() -> None:
    lines = SRC_MD.read_text(encoding="utf-8").splitlines()
    doc = Document()

    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.3)
    sec.bottom_margin = Cm(2.3)
    sec.left_margin = Cm(2.4)
    sec.right_margin = Cm(2.4)
    add_page_number_footer(sec)

    i = 0
    in_abstract = False
    embedded_images = 0
    embedded_tables = 0

    while i < len(lines):
        raw = lines[i].rstrip()
        if not raw or raw.strip() == "---":
            i += 1
            continue

        # 图片语法 ![caption](path)
        img_m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", raw.strip())
        if img_m:
            cap_txt, rel_path = img_m.group(1).strip(), img_m.group(2).strip()
            img_path = (SRC_MD.parent / rel_path).resolve()
            if not img_path.is_file():
                raise FileNotFoundError(f"报告引用图片不存在: {img_path}")

            with Image.open(img_path) as im:
                w_px, h_px = im.size
            max_w_cm, max_h_cm = 15.8, 16.8
            aspect = h_px / max(w_px, 1)
            target_w_cm = max_w_cm
            if target_w_cm * aspect > max_h_cm:
                target_w_cm = max_h_cm / aspect

            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(6)
            p_img.paragraph_format.space_after = Pt(2)
            p_img.paragraph_format.keep_with_next = True
            p_img.add_run().add_picture(str(img_path), width=Cm(target_w_cm))

            if cap_txt:
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_before = Pt(1)
                p_cap.paragraph_format.space_after = Pt(8)
                add_rich_runs(p_cap, cap_txt, size=9.2, base_east=FONT_HEAD, color=(71, 85, 105))
            embedded_images += 1
            i += 1
            continue

        # 独立展示公式块 $$...$$
        if raw.strip().startswith("$$"):
            buf = [raw.strip()]
            if not (raw.strip().endswith("$$") and len(raw.strip()) > 4):
                i += 1
                while i < len(lines) and not lines[i].strip().endswith("$$"):
                    buf.append(lines[i].strip())
                    i += 1
                if i < len(lines):
                    buf.append(lines[i].strip())
            eq_str = " ".join(buf)
            p_eq = doc.add_paragraph()
            p_eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_eq.paragraph_format.space_before = Pt(4)
            p_eq.paragraph_format.space_after = Pt(6)
            add_rich_runs(p_eq, eq_str, size=10.0, base_east=FONT_WEST, color=(15, 23, 42))
            i += 1
            continue

        # Markdown 表格
        if raw.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            header_cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            sep_cells = [c.strip() for c in lines[i + 1].strip().strip("|").split("|")]
            alignments = []
            for sc in sep_cells:
                if sc.startswith(":") and sc.endswith(":"):
                    alignments.append("center")
                elif sc.endswith(":"):
                    alignments.append("right")
                else:
                    alignments.append("left")
            i += 2
            body_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                body_rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1

            all_rows = [header_cells] + body_rows
            ncol = max(len(r) for r in all_rows)
            tbl = doc.add_table(rows=len(all_rows), cols=ncol)
            for ri, rdata in enumerate(all_rows):
                for ci in range(ncol):
                    cell = tbl.cell(ri, ci)
                    cell.text = ""
                    p_c = cell.paragraphs[0]
                    val = rdata[ci] if ci < len(rdata) else ""
                    add_rich_runs(
                        p_c, val,
                        size=8.6 if ncol >= 7 else 9.0,
                        base_east=FONT_HEAD if ri == 0 else FONT_BODY,
                        base_bold=(ri == 0),
                        color=(15, 23, 42) if ri == 0 else (30, 41, 59),
                    )
            style_three_line_table(tbl, alignments)
            p_sp = doc.add_paragraph()
            p_sp.paragraph_format.space_before = Pt(0)
            p_sp.paragraph_format.space_after = Pt(4)
            embedded_tables += 1
            continue

        # 标题
        hm = re.match(r"^(#{1,3})\s+(.*)$", raw)
        if hm:
            lvl, title_txt = len(hm.group(1)), hm.group(2).strip()
            p_h = doc.add_paragraph()
            p_h.paragraph_format.keep_with_next = True
            if lvl == 1:
                p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_h.paragraph_format.space_before = Pt(4)
                p_h.paragraph_format.space_after = Pt(6)
                add_rich_runs(p_h, title_txt, size=17.5, base_east=FONT_HEAD, base_bold=True, color=(31, 58, 95))
            elif lvl == 2:
                in_abstract = (title_txt == "摘要")
                p_h.paragraph_format.space_before = Pt(13)
                p_h.paragraph_format.space_after = Pt(5)
                add_rich_runs(p_h, title_txt, size=13.5, base_east=FONT_HEAD, base_bold=True, color=(31, 58, 95))
                set_paragraph_bottom_border(p_h, color_hex="CBD5E1", sz="6")
            else:
                p_h.paragraph_format.space_before = Pt(9)
                p_h.paragraph_format.space_after = Pt(3)
                add_rich_runs(p_h, title_txt, size=11.5, base_east=FONT_HEAD, base_bold=True, color=(31, 58, 95))
            i += 1
            continue

        # 引用元信息块 > ...
        if raw.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            p_q = doc.add_paragraph()
            p_q.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_q.paragraph_format.space_before = Pt(2)
            p_q.paragraph_format.space_after = Pt(10)
            p_q.paragraph_format.line_spacing = 1.35
            add_rich_runs(p_q, "  |  ".join(quote_lines), size=9.2, base_east=FONT_HEAD, color=(71, 85, 105))
            set_paragraph_bottom_border(p_q, color_hex="0F172A", sz="10")
            continue

        # 有序或无序列表
        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", raw)
        if lm:
            marker, content = lm.group(2), lm.group(3).strip()
            p_l = doc.add_paragraph()
            p_l.paragraph_format.left_indent = Cm(0.75)
            p_l.paragraph_format.first_line_indent = Cm(-0.45)
            p_l.paragraph_format.space_before = Pt(1.5)
            p_l.paragraph_format.space_after = Pt(2.5)
            p_l.paragraph_format.line_spacing = 1.35
            prefix = f"{marker} " if marker[0].isdigit() else "• "
            r_pre = p_l.add_run(prefix)
            set_run_font(r_pre, east_asia=FONT_HEAD, west=FONT_HEAD, size=10.2, bold=True, color=(29, 111, 165))
            add_rich_runs(p_l, content, size=10.2, base_east=FONT_BODY, color=(30, 41, 59))
            i += 1
            continue

        # 普通正文段落
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Pt(21)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.38
        add_rich_runs(p, raw.strip(), size=10.2 if in_abstract else 10.5, base_east=FONT_BODY, color=(30, 41, 59))
        i += 1

    import shutil
    DST_DOCX.parent.mkdir(parents=True, exist_ok=True)
    COPY_D_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(DST_DOCX))
    shutil.copy2(DST_DOCX, COPY_D_DOCX)
    # 同步至 outputs/d/报告.md 时自动修正相对图片层级（../ -> ../../），保证 Markdown 预览图片正常显示
    d_md_text = SRC_MD.read_text(encoding="utf-8").replace("](../", "](../../")
    COPY_D_MD.write_text(d_md_text, encoding="utf-8")
    shutil.copy2(DST_DOCX, OUTER_DOCX)
    print(f"Word 报告已生成：{DST_DOCX}（已同步至 {COPY_D_DOCX} 与 {OUTER_DOCX}，嵌入图片 {embedded_images} 幅，三线表 {embedded_tables} 张）")


if __name__ == "__main__":
    main()
