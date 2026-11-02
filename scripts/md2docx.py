#!/usr/bin/env python3
"""极简 md → docx：只处理本项目用到的语法（标题/段落/表格/列表/引用/粗体/行内码）。"""
import re, sys
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

BODY, HEAD, CODE = '宋体', '黑体', 'Consolas'


def set_font(run, name=BODY, size=10.5, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)


def add_inline(p, text, size=10.5, base_bold=False, color=None):
    """处理 **粗体** 和 `代码`。"""
    for tok in re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)', text):
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**'):
            r = p.add_run(tok[2:-2]); set_font(r, HEAD, size, True, color)
        elif tok.startswith('*') and tok.endswith('*'):
            r = p.add_run(tok[1:-1]); set_font(r, BODY, size, base_bold, color); r.font.italic = True
        elif tok.startswith('`') and tok.endswith('`'):
            r = p.add_run(tok[1:-1]); set_font(r, CODE, size - 0.5, base_bold, color)
        else:
            r = p.add_run(tok); set_font(r, BODY, size, base_bold, color)


def main(src, dst):
    lines = open(src, encoding='utf-8').read().split('\n')
    doc = Document()
    st = doc.styles['Normal']
    st.font.name = BODY; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), BODY)

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln or ln.strip() == '---':
            i += 1; continue

        # 表格
        if ln.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:\-|]+\|$', lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not re.match(r'^[\s:\-]+$', ''.join(cells)):
                    rows.append(cells)
                i += 1
            ncol = max(len(r) for r in rows)
            t = doc.add_table(rows=len(rows), cols=ncol)
            t.style = 'Table Grid'
            for ri, row in enumerate(rows):
                for ci in range(ncol):
                    cell = t.cell(ri, ci)
                    cell.text = ''
                    p = cell.paragraphs[0]
                    add_inline(p, row[ci] if ci < len(row) else '', size=9, base_bold=(ri == 0))
            doc.add_paragraph()
            continue

        # 代码块
        if ln.startswith('```'):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i].rstrip('\n'))
                i += 1
            i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(10)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(8)
            r = p.add_run('\n'.join(buf))
            set_font(r, CODE, 9)
            continue

        # 标题
        m = re.match(r'^(#{1,4})\s+(.*)', ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2)
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12 if lvl <= 2 else 8)
            p.paragraph_format.space_after = Pt(4)
            add_inline(p, txt, size={1: 18, 2: 14, 3: 12, 4: 11}[lvl], base_bold=True, color=(0x1F, 0x3A, 0x5F) if lvl <= 2 else None)
            i += 1; continue

        # 引用
        if ln.startswith('>'):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(16)
            add_inline(p, ln.lstrip('> ').strip(), size=9.5, color=(0x66, 0x66, 0x66))
            i += 1; continue

        # 列表
        m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', ln)
        if m:
            indent = len(m.group(1))
            style = 'List Number' if re.match(r'\d+\.', m.group(2)) else 'List Bullet'
            p = doc.add_paragraph(style=style)
            p.paragraph_format.left_indent = Pt(18 + indent * 10)
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, m.group(3), size=10)
            i += 1; continue

        # 普通段落
        p = doc.add_paragraph()
        add_inline(p, ln)
        i += 1

    doc.save(dst)
    print('saved', dst)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
