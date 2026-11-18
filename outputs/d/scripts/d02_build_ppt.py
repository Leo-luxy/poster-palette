"""构建 12 页 16:9 宽屏课程汇报演示文稿 docs/汇报.pptx 与配套逐页讲稿 docs/汇报.md。"""
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[3]
DST_PPTX = ROOT / "docs" / "汇报.pptx"
DST_MD = ROOT / "docs" / "汇报.md"
COPY_D_PPTX = ROOT / "outputs" / "d" / "汇报.pptx"
COPY_D_MD = ROOT / "outputs" / "d" / "汇报.md"
OUTER_PPTX = ROOT.parent / "汇报.pptx"

SLIDE_W = 13.333
SLIDE_H = 7.500

FONT_CN = "微软雅黑"
FONT_EN = "Calibri"
FONT_MONO = "Consolas"

# 统一全组学术色板（严格对齐 scripts/common.py 与报告）
C_NAVY = RGBColor(31, 58, 95)       # #1F3A5F 主学术深蓝
C_DARK = RGBColor(15, 23, 42)       # #0F172A 墨黑标题
C_TEXT = RGBColor(30, 41, 59)       # #1E293B 正文深灰蓝
C_MUTED = RGBColor(100, 116, 139)   # #64748B 辅助说明灰
C_BG = RGBColor(248, 250, 252)      # #F8FAFC 幻灯片浅灰白底
C_WHITE = RGBColor(255, 255, 255)   # #FFFFFF 纯白卡片底
C_BORDER = RGBColor(203, 213, 225)  # #CBD5E1 卡片细边框
C_SOFT_BLUE = RGBColor(239, 246, 255)
C_SOFT_AMBER = RGBColor(255, 247, 237)
C_SOFT_GREEN = RGBColor(240, 253, 244)
C_SOFT_RED = RGBColor(254, 242, 242)

C_BLUE = RGBColor(43, 123, 186)     # #2B7BBA 科幻/冷调蓝
C_ORANGE = RGBColor(217, 95, 2)     # #D95F02 爱情/暖调橙
C_GREEN = RGBColor(46, 139, 87)     # #2E8B57 恐怖/稳健绿
C_RED = RGBColor(185, 28, 28)       # #B91C1C 警示/零相关红
C_GOLD = RGBColor(180, 130, 25)     # 喜剧暖金
C_SLATE = RGBColor(71, 85, 105)     # 深暗低彩灰蓝


SPEAKER_NOTES: list[tuple[str, str]] = [
    (
        "第 1 页｜封面：海报会说话",
        "各位老师、同学好！今天我们小组汇报的题目是《海报会说话——电影海报配色的类型结构、时间演变与地区差异》。围绕「观众第一眼看到的海报配色究竟传递了什么信息」，我们采集并清洗了 TMDB 1950 至 2025 年间 19,700 部主流电影与 19,694 张原语言海报，从结构、时间、效用、空间四个正交维度完成了全流程实证检验。",
    ),
    (
        "第 2 页｜一句话总纲与四维核心发现",
        "先给出全文的一句话总纲：电影海报配色是帮助观众快速识别题材的「类型视觉编码」，随年代与地区系统性迁移，但与影片口碑均分几乎无关（相关系数绝对值全部小于 0.08）。具体对应四条定量结论：第一，类型结构上，明度是区分类型最强的单一指标（爱情比恐怖平均亮 0.199），无监督聚类进一步收敛出四类全行业共享色型模板；第二，时间维度上，七十六年间整体变暗、青蓝占比扩张 10.3 个百分点，但 2020 年后饱和度显著回升 0.0424，并非一路变灰；第三，效用维度上，色彩指标对评分的解释方差不足千分之三；第四，空间维度上，法意日整体偏亮且日本暖色占比最低（37.5%），韩华偏暗且韩国饱和度最低。",
    ),
    (
        "第 3 页｜研究问题与四维正交分析框架",
        "日常观影中有很多经验判断，例如「科幻片偏蓝、恐怖片偏暗」「现代海报越来越流行青橙暗调」「高分佳作配色更克制」。我们将这些直觉拆解为结构、时间、效用、空间四个正交问题，统一以「单部电影」为统计单元（一片一票），建立从动态采样、去本地化换图、近灰像素掩膜到电影级 Bootstrap 置信区间的闭环。",
    ),
    (
        "第 4 页｜数据构建：动态 2.6% 分位门槛与原语言海报去本地化",
        "在数据构建阶段，我们解决了两个极易被忽视的系统性偏差。第一是跨年代幸存者偏差：第一版用固定 200 票门槛时，2010 年代有 2.8% 的电影过线，而 1950 年代只有前 0.9% 的影史经典过线；第二版改为按每年有票电影前 2.6% 动态截取（门槛 44 到 268 票），把八个年代的实际通过率拉平在 2.61% 到 3.06%，共入库 19,700 部。第二是海报本地化污染：默认中文接口混入了 41% 的中文宣发海报，且 2020 年代高达 69%；我们遍历图库将 8,000 张本地化海报替换为原语言版，确保跨年代与跨国对比不被中文字幕排版干扰。",
    ),
    (
        "第 5 页｜特征工程与统计方法：近灰像素掩膜与联合重采样",
        "特征提取有三个关键设计。一是裁去底部 12% 演职员表文字区；二是在 HSV 空间引入 S ≥ 0.20 的「近灰像素掩膜」——这是本项目的核心技术细节，因为黑白灰像素的色相角完全受压缩噪声支配，不加掩膜会把主色全部拉向纯黑并污染色相分布；三是涉及色相与聚类时统一施加 sat_frac ≥ 0.10 闸门（保留 19,072 部）。统计推断上，针对一部电影含多个类型标签的重叠问题，采用 1,000 次电影级联合 Bootstrap；无监督聚类则构造五维圆锥色度坐标 Conic_5D，消除 0° 与 360° 周期断层。",
    ),
    (
        "第 6 页｜发现一（结构 · 做法 A）：预设类型的明度阶梯与冷暖分野",
        "先看预设类型对比。明度拉开了近 0.23 的清晰阶梯：喜剧（0.6305）、动画（0.6082）、爱情（0.6034）高调明亮，科幻（0.4835）、惊悚（0.4401）、恐怖（0.4044）依次下探，互斥子集明度效应量 η²_H 达 0.219，远超饱和度与丰富度。色相上，爱情片在 0°–60° 暖色占比达 54.2%（比科幻高 14.8 个百分点），科幻与动画在 180°–240° 青蓝波段均超过 32%（科幻比爱情高 11.1 个百分点），恐怖片则在 90°–150° 黄绿冷绿区显著偏高。",
    ),
    (
        "第 7 页｜发现一（结构 · 做法 B）：无监督四类客观色型与典型海报色卡",
        "如果不告诉算法任何类型标签，数据本身会聚成几类？在 45 组基准测试中，Conic_5D 配合 K-Means 在 k=4 时取得最低 DB 指数（1.1803）与 0.9913 的子样本一致性 ARI，收敛出明亮浅调（28.7%）、浓烈暖调（25.9%）、青蓝冷调（19.4%）和深暗低彩（26.0%）四类客观色型。右图展示了各类中心海报的 14×10 抽象色卡。关键结论是：电影工业并非一个类型独占一种颜色，而是共享这四套基础色型模板，爱情喜剧重配明亮浅调（约 40%），动画科幻重配青蓝与高彩，恐怖惊悚重配深暗低彩（超 40%）。",
    ),
    (
        "第 8 页｜发现二（时间 · 图 2）：1950—2025 年长期变暗与饱和度非单调波动",
        "再看七十六年的时间演变。对比完整十年，2010 年代较 1950 年代平均明度下降 0.0705，色彩丰富度下降 16.88；色相上 0°–60° 红黄暖色由 58.6% 降至 47.8%，180°–240° 青蓝由 17.4% 升至 27.7%。但右图的五年窗口中位数曲线表明演变绝非单调线性：2020 至 2025 年明度继续走低，平均饱和度却逆势回升 0.0424——流媒体小缩略图竞争在压暗背景的同时强化了高饱和局部撞色。注意右图阴影是片间四分位距 IQR，代表同年代内部多样性。",
    ),
    (
        "第 9 页｜发现三（效用 · 图 3）：配色不预测口碑——显著性与效应量解耦",
        "既然配色分化这么明显，更暗或更克制的海报会不会评分更高？在 19,592 部有效评分电影上，明度（r=+0.047）、饱和度（r=−0.052）、丰富度（r=−0.045）与 TMDB 均分的相关系数全部落在 ±0.08 以内，分八大类型看也全部贴着 0。这里展示了大样本统计的经典启示：两万样本下 r=0.047 也会算出 p < 10^-10，但决定系数不到千分之三，明度横跨全区间均分只差 0.19 分。因此配色是传递题材预期的分类信号，而不是质量信号。",
    ),
    (
        "第 10 页｜发现四（空间 · 图 4）：2001—2025 年七大国家／地区组配色差异",
        "空间维度聚焦数字宣发成熟的 2001—2025 年，结合制片国与原语言将 10,115 部电影唯一归入七组。以美国组（明度 0.5193）为参照，法国（+0.0598）、意大利（+0.0715）和日本（+0.0470）显著偏亮，且日本组 0°–60° 暖色占比仅 37.5%、青蓝达 33.0%，与日本动画及青春奇幻题材占比高一致；华语组（−0.0511）与韩国组（−0.0772）显著偏暗，韩国饱和度低出 0.1032，对应韩国外输热门片中犯罪惊悚题材的高占比。这属于入库样本构成描述，不做民族文化因果推断。",
    ),
    (
        "第 11 页｜稳健性核验与五大研究局限（Threats to Validity）",
        "为确保结论可靠，我们完成了三项敏感性核验：在每张海报内屏蔽 0°–60° 人脸肤色高发区重归一后，科幻青蓝优势（46.8% vs 爱情 39.9%）依然稳固；近灰阈值从 0.05 扫至 0.20 差值波动小于 0.3 个百分点；剔除多标签重叠片后结论不变。右侧列出五项研究边界：上映年不等于海报设计年（老片可能含蓝光重映图）、手绘石版到数字合成的媒介混杂、国家归属未剥离片种结构、整幅聚合未分离前背景，以及 TMDB 欧美用户偏倚与近期新片右删失。",
    ),
    (
        "第 12 页｜总结、全组模块分工与可复现流水线（Q&A）",
        "最后总结全组工作：A 负责动态分位采集、8,000 张海报去本地化与图 3 口碑分析；B 负责类型对比、45 组圆锥色度无监督聚类与抽象色卡；C 负责七十六年时间演变与七国空间对比；D 负责视觉规范、万字报告统稿与 12 页演示文稿。全仓库遵循 data/ 只读契约，配有 100 余项自动化断言核验，无需联网即可一键复现全部图表与文档。汇报完毕，感谢各位老师和同学，欢迎提问！",
    ),
]


def set_run_style(run, size: float, bold: bool = False, italic: bool = False, color: RGBColor = C_TEXT, font_cn: str = FONT_CN, font_en: str = FONT_EN) -> None:
    run.font.name = font_en
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        from lxml import etree
        ea = etree.SubElement(rPr, qn("a:ea"))
    ea.set("typeface", font_cn)


def add_box(slide, x: float, y: float, w: float, h: float, fill: RGBColor | None = C_WHITE, border: RGBColor | None = C_BORDER, border_pt: float = 0.75, rounded: bool = False):
    stype = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(stype, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded and shp.adjustments:
        shp.adjustments[0] = 0.06
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if border is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = border
        shp.line.width = Pt(border_pt)
    return shp


def add_textbox(slide, x: float, y: float, w: float, h: float, lines: list[tuple[str, float, bool, RGBColor]], line_spacing: float = 1.22, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, pad_lr: float = 0.06, pad_tb: float = 0.04):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(pad_lr)
    tf.margin_right = Inches(pad_lr)
    tf.margin_top = Inches(pad_tb)
    tf.margin_bottom = Inches(pad_tb)
    for idx, (txt, sz, bld, col) in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = txt
        set_run_style(r, size=sz, bold=bld, color=col)
    return tb


def add_rich_paragraph(tf, segments: list[tuple[str, float, bool, RGBColor, str]], first: bool = False, space_after: float = 3.0, line_spacing: float = 1.24, align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.line_spacing = line_spacing
    for txt, sz, bld, col, fmode in segments:
        r = p.add_run()
        r.text = txt
        if fmode == "mono":
            set_run_style(r, size=sz, bold=bld, color=col, font_cn=FONT_MONO, font_en=FONT_MONO)
        else:
            set_run_style(r, size=sz, bold=bld, color=col)
    return p


def add_fitted_picture(slide, img_path: Path, box_x: float, box_y: float, box_w: float, box_h: float, with_card: bool = True, pad: float = 0.08):
    if not img_path.is_file():
        raise FileNotFoundError(f"PPT 引用图片不存在: {img_path}")
    if with_card:
        add_box(slide, box_x, box_y, box_w, box_h, fill=C_WHITE, border=C_BORDER, border_pt=0.85, rounded=False)
    ix = box_x + (pad if with_card else 0.0)
    iy = box_y + (pad if with_card else 0.0)
    iw = box_w - (2 * pad if with_card else 0.0)
    ih = box_h - (2 * pad if with_card else 0.0)
    with Image.open(img_path) as im:
        pw, ph = im.size
    scale = min(iw / pw, ih / ph)
    dw = pw * scale
    dh = ph * scale
    cx = ix + (iw - dw) / 2.0
    cy = iy + (ih - dh) / 2.0
    # 仅传 width，保持严格原始宽高比，零拉伸变形
    return slide.shapes.add_picture(str(img_path), Inches(cx), Inches(cy), width=Inches(dw))


def apply_slide_chrome(slide, page_no: int, badge_text: str, action_title: str) -> None:
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_BG

    # 顶部三段式品牌色带
    add_box(slide, 0.0, 0.0, 9.4, 0.06, fill=C_NAVY, border=None)
    add_box(slide, 9.4, 0.0, 2.4, 0.06, fill=C_BLUE, border=None)
    add_box(slide, 11.8, 0.0, 1.533, 0.06, fill=C_ORANGE, border=None)

    # 章节胶囊标签
    pill = add_box(slide, 0.50, 0.19, 1.85, 0.27, fill=C_SOFT_BLUE, border=C_BLUE, border_pt=0.6, rounded=True)
    tf_p = pill.text_frame
    tf_p.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_p.margin_left = tf_p.margin_right = Inches(0.04)
    tf_p.margin_top = tf_p.margin_bottom = Inches(0.0)
    p0 = tf_p.paragraphs[0]
    p0.alignment = PP_ALIGN.CENTER
    r0 = p0.add_run()
    r0.text = badge_text
    set_run_style(r0, size=9.5, bold=True, color=C_NAVY)

    # 结论式主标题（Action Title）
    add_textbox(
        slide, 0.50, 0.49, 12.33, 0.48,
        [(action_title, 18.5, True, C_DARK)],
        line_spacing=1.12, pad_lr=0.0, pad_tb=0.02,
    )

    # 标题底部分隔细线
    add_box(slide, 0.50, 1.02, 12.33, 0.012, fill=C_BORDER, border=None)

    # 页脚
    add_box(slide, 0.50, 7.12, 12.33, 0.01, fill=C_BORDER, border=None)
    add_textbox(
        slide, 0.50, 7.15, 10.2, 0.28,
        [("数据分析实践 · 海报会说话：19,700 部电影与 19,694 张原语言海报实证研究（1950—2025）", 8.8, False, C_MUTED)],
        pad_lr=0.0, pad_tb=0.0,
    )
    add_textbox(
        slide, 11.10, 7.15, 1.73, 0.28,
        [(f"{page_no:02d} / 12", 9.2, True, C_NAVY)],
        align=PP_ALIGN.RIGHT, pad_lr=0.0, pad_tb=0.0,
    )


def style_ppt_table(tbl, col_widths: list[float], alignments: list, body_font_pt: float = 9.5, head_font_pt: float = 10.0) -> None:
    for ci, w in enumerate(col_widths):
        tbl.columns[ci].width = Inches(w)
    nrow = len(tbl.rows)
    for ri in range(nrow):
        for ci in range(len(col_widths)):
            cell = tbl.cell(ri, ci)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)
            cell.fill.solid()
            if ri == 0:
                cell.fill.fore_color.rgb = C_NAVY
            elif ri % 2 == 1:
                cell.fill.fore_color.rgb = C_WHITE
            else:
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)
            p = cell.text_frame.paragraphs[0]
            p.alignment = alignments[ci]
            p.line_spacing = 1.15
            txt = cell.text
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            p.alignment = alignments[ci]
            r = p.add_run()
            r.text = txt
            set_run_style(
                r,
                size=head_font_pt if ri == 0 else body_font_pt,
                bold=(ri == 0 or ci == 0),
                color=C_WHITE if ri == 0 else (C_NAVY if ci == 0 else C_TEXT),
            )


def add_metric_card(slide, x: float, y: float, w: float, h: float, accent: RGBColor, tag: str, kpi: str, bullets: list[str], kpi_pt: float = 15.0, body_pt: float = 10.0) -> None:
    add_box(slide, x, y, w, h, fill=C_WHITE, border=C_BORDER, border_pt=0.8)
    add_box(slide, x, y, 0.08, h, fill=accent, border=None)
    tb = slide.shapes.add_textbox(Inches(x + 0.16), Inches(y + 0.08), Inches(w - 0.24), Inches(h - 0.14))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    add_rich_paragraph(tf, [(tag, 9.5, True, accent, "cn")], first=True, space_after=2)
    add_rich_paragraph(tf, [(kpi, kpi_pt, True, C_DARK, "cn")], space_after=5, line_spacing=1.15)
    for b in bullets:
        add_rich_paragraph(tf, [("• ", body_pt, True, accent, "cn"), (b, body_pt, False, C_TEXT, "cn")], space_after=3, line_spacing=1.24)


def build_slides(prs: Presentation) -> None:
    blank = prs.slide_layouts[6]

    # =========================================================================
    # Slide 1: 封面
    # =========================================================================
    s1 = prs.slides.add_slide(blank)
    bg1 = s1.background
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_DARK
    add_box(s1, 0.0, 0.0, 7.65, 7.50, fill=RGBColor(18, 34, 58), border=None)
    add_box(s1, 7.65, 0.0, 5.683, 7.50, fill=C_BG, border=None)
    add_box(s1, 7.65, 0.0, 0.07, 7.50, fill=C_ORANGE, border=None)

    # 左侧 12 色相装饰光谱条
    spectrum_rgb = [
        (220, 88, 66), (229, 152, 56), (218, 196, 68), (144, 201, 78),
        (72, 185, 96), (62, 186, 156), (64, 173, 214), (66, 118, 212),
        (106, 84, 206), (162, 82, 201), (209, 82, 163), (218, 78, 112),
    ]
    sw = 6.48 / 12.0
    for idx, rgb in enumerate(spectrum_rgb):
        add_box(s1, 0.62 + idx * sw, 1.15, sw + 0.005, 0.09, fill=RGBColor(*rgb), border=None)

    add_textbox(
        s1, 0.62, 1.42, 6.60, 0.40,
        [("数据分析实践 · 课程大作业汇报", 12.0, True, RGBColor(147, 197, 253))],
        pad_lr=0.0,
    )
    add_textbox(
        s1, 0.62, 1.92, 6.65, 1.85,
        [
            ("海报会说话", 38.0, True, C_WHITE),
            ("电影海报配色的类型结构、时间演变与地区差异", 19.0, True, RGBColor(226, 232, 240)),
        ],
        line_spacing=1.25, pad_lr=0.0,
    )
    add_textbox(
        s1, 0.62, 3.95, 6.55, 0.95,
        [("基于 TMDB 1950—2025 年动态 2.6% 分位门槛构建样本池，结合近灰像素掩膜、圆锥色度无监督聚类与电影级 Bootstrap 检验的四维实证研究", 11.2, False, RGBColor(186, 204, 226))],
        line_spacing=1.38, pad_lr=0.0,
    )

    # 四个核心样本指标徽章
    kpis_cover = [
        ("1950—2025", "76 年时间跨度"),
        ("19,700 部", "动态前 2.6% 入库电影"),
        ("19,694 张", "去本地化原语言海报"),
        ("4 维闭环", "结构 · 时间 · 效用 · 空间"),
    ]
    for idx, (v_txt, l_txt) in enumerate(kpis_cover):
        bx = 0.62 + (idx % 2) * 3.28
        by = 5.10 + (idx // 2) * 0.82
        add_box(s1, bx, by, 3.12, 0.68, fill=RGBColor(28, 50, 82), border=RGBColor(59, 92, 138), border_pt=0.75, rounded=True)
        add_textbox(
            s1, bx + 0.12, by + 0.06, 2.88, 0.56,
            [(v_txt, 13.5, True, RGBColor(253, 186, 116)), (l_txt, 9.2, False, RGBColor(203, 213, 225))],
            line_spacing=1.12, pad_lr=0.02, pad_tb=0.0,
        )

    add_textbox(
        s1, 0.62, 6.86, 6.60, 0.36,
        [("联合交付模块：A（数据与口碑）· B（类型与色型聚类）· C（时间与跨国对比）· D（报告统稿与演示）", 9.2, False, RGBColor(148, 163, 184))],
        pad_lr=0.0,
    )

    # 右侧嵌入竖版 12 幅海报抽象色卡总览图 + 图注卡（0.878 宽高比完美填充竖框）
    add_fitted_picture(s1, ROOT / "figures" / "b" / "fig_q1_palettes.png", 7.98, 0.45, 5.05, 5.72, with_card=True, pad=0.08)
    add_box(s1, 7.98, 6.30, 5.05, 0.74, fill=C_WHITE, border=C_BORDER, border_pt=0.75)
    add_textbox(
        s1, 8.08, 6.36, 4.85, 0.62,
        [
            ("视觉预览：无监督四类客观色型与八类主流电影中心海报 14×10 色卡", 9.5, True, C_NAVY),
            ("在不输入任何题材标签的 HSV 圆锥空间自动浮现的四套基础配色模板", 8.8, False, C_MUTED),
        ],
        line_spacing=1.18, pad_lr=0.02, pad_tb=0.0,
    )

    # =========================================================================
    # Slide 2: 一句话总纲与四维核心发现速览
    # =========================================================================
    s2 = prs.slides.add_slide(blank)
    apply_slide_chrome(s2, 2, "01 · 核心结论速览", "一句话总纲：海报配色是识别题材的「类型信号」，随时代与地区迁移，但不预测口碑")

    add_box(s2, 0.50, 1.16, 12.33, 0.82, fill=C_NAVY, border=None, rounded=True)
    tb2 = s2.shapes.add_textbox(Inches(0.70), Inches(1.23), Inches(11.93), Inches(0.68))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    tf2.vertical_anchor = MSO_ANCHOR.MIDDLE
    add_rich_paragraph(
        tf2,
        [
            ("全文核心实证判断：", 12.0, True, RGBColor(253, 186, 116), "cn"),
            ("电影工业共享「明亮浅调、浓烈暖调、青蓝冷调、深暗低彩」四套基础色型模板；不同类型与地区通过改变模板配比建立鲜明视觉预期，七十六年间整体向低明度与青蓝波段演进（近期饱和度回弹），但色彩指标与观众评分的相关系数全部落在 ", 11.2, False, C_WHITE, "cn"),
            ("±0.08", 11.5, True, RGBColor(253, 186, 116), "cn"),
            (" 以内。", 11.2, False, C_WHITE, "cn"),
        ],
        first=True, space_after=0, line_spacing=1.26,
    )

    cards_s2 = [
        (
            0.50, 2.16, C_ORANGE, "维度一｜结构（类型对比 & 无监督聚类）",
            "明度跨度 +0.199 · 四类共享客观色型（ARI = 0.991）",
            [
                "明度是区分类型最强单一指标（互斥子集 η²_H = 0.2193）：喜剧 0.6305、动画 0.6082、爱情 0.6034 依次偏亮，恐怖低至 0.4044。",
                "爱情 0°–60° 暖色较科幻高 +14.83pp，科幻 180°–240° 青蓝高 +11.09pp；屏蔽肤色区重归一后格局不变。",
                "无监督 Conic_5D K-Means(k=4) 收敛出四类色型，各题材靠调配四类模板比例建立识别度。",
            ],
        ),
        (
            6.78, 2.16, C_BLUE, "维度二｜时间（1950—2025 年全球演变）",
            "长期变暗 −0.0705 · 近期饱和度逆势回升 +0.0424",
            [
                "2010s 相对 1950s：平均明度降 0.0705 [−0.0835, −0.0588]，色彩丰富度降 16.88 [−19.33, −14.57]。",
                "色相显著冷化：0°–60° 暖色由 58.6% 降至 47.8%，180°–240° 青蓝由 17.4% 升至 27.7%（+10.3pp）。",
                "五年移动窗口揭示非单调性：2020–2025 较 2010s 明度续降 −0.0364，饱和度显著回升 +0.0424，否定「一路变灰」。",
            ],
        ),
        (
            0.50, 4.66, C_RED, "维度三｜效用（19,592 部电影口碑检验）",
            "相关系数 |r| < 0.08 · 决定系数 R² < 0.3%（零预测力）",
            [
                "全库明度 r = +0.047、饱和度 r = −0.052、丰富度 r = −0.045；分八大类型内部 |r| 最高仅 0.079。",
                "明度从 0 到 1 全程跨度仅对应均分变化 0.19 分，业务效应近似为零。",
                "大样本方法论启示：N=19,592 时微弱相关亦呈 p < 10⁻¹⁰，必须严格解耦「统计显著」与「效应量大小」。",
            ],
        ),
        (
            6.78, 4.66, C_GREEN, "维度四｜空间（2001—2025 年七大国家／地区组）",
            "法意日偏亮（日本暖色仅 37.5%）· 韩华显著偏暗冷",
            [
                "基于制片国与原语言唯一归属 10,115 部影片，以美国组（V=0.5193, S=0.4156）为共同参照系。",
                "法国（+0.0598）、意大利（+0.0715）、日本（+0.0470）显著更亮；日本 180°–240° 青蓝达 33.02%。",
                "华语组（−0.0511）与韩国组（−0.0772）更暗，韩国平均饱和度低出 −0.1032 [−0.1240, −0.0825]。",
            ],
        ),
    ]
    for cx, cy, acc, tag, kpi, buls in cards_s2:
        add_metric_card(s2, cx, cy, 6.05, 2.34, acc, tag, kpi, buls, kpi_pt=13.8, body_pt=9.6)

    # =========================================================================
    # Slide 3: 研究问题与四维正交分析框架
    # =========================================================================
    s3 = prs.slides.add_slide(blank)
    apply_slide_chrome(s3, 3, "02 · 问题与框架", "研究设计：将行业经验直觉拆解为四个正交实证维度，统一以「单部电影」为统计单元")

    # 左侧：直觉 vs 检验卡片
    add_box(s3, 0.50, 1.18, 4.25, 4.58, fill=C_WHITE, border=C_BORDER, border_pt=0.8)
    add_box(s3, 0.50, 1.18, 4.25, 0.42, fill=C_NAVY, border=None)
    add_textbox(s3, 0.62, 1.23, 4.00, 0.32, [("从行业经验直觉到可证伪统计命题", 11.0, True, C_WHITE)], pad_lr=0.0, pad_tb=0.0)

    intuitions = [
        ("直觉 1｜题材套路", "「科幻必蓝、恐怖必暗绿、爱情必粉暖」？\n→ 检验预设差值 CI，并测试无标签聚类能否自动还原题材。"),
        ("直觉 2｜时代变迁", "「现代电影海报越来越灰暗单调」？\n→ 追踪 76 年长周期轨迹，区分线性单调趋势与阶段性拐点。"),
        ("直觉 3｜高级感迷思", "「低饱和克制配色更容易拿高分」？\n→ 在近两万部样本上分离 p 值显著性与解释方差 R²。"),
        ("直觉 4｜地域风格", "「日系清新亮蓝、韩系冷峻低饱和」？\n→ 控制在 2001—2025 同代窗口，按唯一归属规则量化组差。"),
    ]
    tb_i = s3.shapes.add_textbox(Inches(0.64), Inches(1.70), Inches(3.98), Inches(3.95))
    tf_i = tb_i.text_frame
    tf_i.word_wrap = True
    for idx, (hd, bd) in enumerate(intuitions):
        add_rich_paragraph(tf_i, [(hd, 10.2, True, C_ORANGE if idx % 2 == 0 else C_BLUE, "cn")], first=(idx == 0), space_after=1)
        add_rich_paragraph(tf_i, [(bd, 9.3, False, C_TEXT, "cn")], space_after=7, line_spacing=1.22)

    # 右侧：四维正交设计矩阵表
    tbl_shape3 = s3.shapes.add_table(5, 5, Inches(4.95), Inches(1.18), Inches(7.88), Inches(4.58))
    rows_s3 = [
        ["分析维度", "核心实证问题", "有效样本口径", "核心统计与建模方法", "定稿主图"],
        ["结构维度\n（成员 B）", "不同类型配色如何分化？无标签数据聚出几类色型？", "全指标 19,694 部\n色相有效 19,072 部", "电影级联合 Bootstrap (1,000 次)\n互斥 KW η²_H · Conic_5D K-Means", "图 1a / 1b / 1c\n附录图 A1"],
        ["时间维度\n（成员 C）", "1950—2025 年全球海报色彩如何演变？是否单调？", "全期 19,694 部\n8 个年代分箱", "居中 5 年窗口中位数与 IQR\n年代差值 Bootstrap · Theil–Sen", "图 2a / 2b / 2c"],
        ["效用维度\n（成员 A）", "明暗、饱和度或丰富度能否预测观众评分均分？", "有评分且非纯黑\n19,592 部", "OLS 线性回归 · Pearson r\n分八大类型 95% CI 与效应量审计", "图 3"],
        ["空间维度\n（成员 C）", "2001—2025 年美英法意日华韩七组是否存在显著差异？", "2001—2025 年\n唯一归属 10,115 部", "制片国 + 原语言唯一归属规则\n以美国为参照系 Bootstrap 均值差", "图 4a / 4b / 4c"],
    ]
    for r_i, r_vals in enumerate(rows_s3):
        for c_i, val in enumerate(r_vals):
            tbl_shape3.table.cell(r_i, c_i).text = val
    style_ppt_table(
        tbl_shape3.table,
        [1.18, 2.12, 1.48, 2.02, 1.08],
        [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.CENTER],
        body_font_pt=9.1, head_font_pt=9.8,
    )

    # 底部流水线横条
    steps_s3 = [
        ("1. 动态 2.6% 分位采集", "消除跨年代幸存者偏差（19,700 部）", C_NAVY),
        ("2. 原语言海报去本地化", "替换 8,000 张中文化海报（19,694 张）", C_BLUE),
        ("3. 底部裁剪 + 近灰掩膜", "切除底部 12% · S ≥ 0.20 提纯色相", C_ORANGE),
        ("4. 不确定性与稳健性闭环", "1,000 次重采样 CI + 肤色/阈值扫描", C_GREEN),
    ]
    for idx, (st_hd, st_sub, st_col) in enumerate(steps_s3):
        sx = 0.50 + idx * 3.12
        add_box(s3, sx, 5.94, 2.97, 0.98, fill=C_WHITE, border=st_col, border_pt=1.1, rounded=True)
        add_textbox(
            s3, sx + 0.10, 6.02, 2.77, 0.82,
            [(st_hd, 10.2, True, st_col), (st_sub, 8.9, False, C_TEXT)],
            line_spacing=1.22, pad_lr=0.02, pad_tb=0.0,
        )

    # =========================================================================
    # Slide 4: 数据构建：动态 2.6% 分位门槛与原语言海报去本地化
    # =========================================================================
    s4 = prs.slides.add_slide(blank)
    apply_slide_chrome(s4, 4, "03 · 数据采集与去偏", "数据工程：用「每年票数前 2.6%」消除幸存者偏差，替换 8,000 张本地化海报还原真实原貌")

    # 左侧说明卡 + 精简年代通过率表
    add_box(s4, 0.50, 1.18, 4.85, 2.78, fill=C_WHITE, border=C_BORDER, border_pt=0.8)
    tb4 = s4.shapes.add_textbox(Inches(0.64), Inches(1.26), Inches(4.58), Inches(2.62))
    tf4 = tb4.text_frame
    tf4.word_wrap = True
    add_rich_paragraph(tf4, [("纠偏一｜为什么不用固定 vote_count ≥ 200？", 10.6, True, C_NAVY, "cn")], first=True, space_after=2)
    add_rich_paragraph(tf4, [("• v1 固定 200 票在 2010s 占前 2.8%（商业主流池），但在 1950s 仅占前 0.9%（261 部传世经典），造成跨年代阶层混杂。\n• v2 改为逐年取有投票电影前 2.6% 分位动态门槛（44–268 票），各年代实际通过率拉平在 2.61%–3.06%，入库 19,700 部。", 9.2, False, C_TEXT, "cn")], space_after=6, line_spacing=1.22)
    add_rich_paragraph(tf4, [("纠偏二｜为什么要做原语言海报去本地化？", 10.6, True, C_ORANGE, "cn")], space_after=2)
    add_rich_paragraph(tf4, [("• zh-CN 接口默认混入 41% 中文版海报（1950s 12.5% → 2020s 69%），本土大字排版严重干扰跨期与跨国对比。\n• 遍历图库按「原语言版 (7,724) → 无文字 (180) → 英文 (96)」替换 8,000 张海报；换图 |Δmean_v| 中位数 0.050，v2 年代跨度更真实。", 9.2, False, C_TEXT, "cn")], space_after=0, line_spacing=1.22)

    tbl_s4 = s4.shapes.add_table(6, 4, Inches(0.50), Inches(4.10), Inches(4.85), Inches(2.84))
    rows_s4 = [
        ["年代（节选）", "动态票数门槛", "入库片数 / 总片库", "实际通过率"],
        ["1950s", "48–72 票", "868 / 28,398", "3.06%"],
        ["1970s", "49–72 票", "1,591 / 56,883", "2.80%"],
        ["1990s", "100–159 票", "2,060 / 75,252", "2.74%"],
        ["2010s", "144–268 票", "5,529 / 197,919", "2.79%"],
        ["全库合计 (8 年代)", "44–268 票", "19,700 / 718,549", "2.74%"],
    ]
    for r_i, r_vals in enumerate(rows_s4):
        for c_i, val in enumerate(r_vals):
            tbl_s4.table.cell(r_i, c_i).text = val
    style_ppt_table(
        tbl_s4.table,
        [1.35, 1.12, 1.43, 0.95],
        [PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
        body_font_pt=8.8, head_font_pt=9.2,
    )

    # 右侧上下双图（严格等比）
    add_fitted_picture(s4, ROOT / "outputs" / "a" / "poster_lang_effect.png", 5.52, 1.18, 7.31, 2.80, with_card=True, pad=0.07)
    add_fitted_picture(s4, ROOT / "outputs" / "a" / "v1_vs_v2.png", 5.52, 4.14, 7.31, 2.80, with_card=True, pad=0.07)

    # =========================================================================
    # Slide 5: 特征工程与统计方法：近灰像素掩膜与联合重采样
    # =========================================================================
    s5 = prs.slides.add_slide(blank)
    apply_slide_chrome(s5, 5, "04 · 特征与统计方法", "方法亮点：用 S ≥ 0.20 近灰像素掩膜剥离压缩噪声，以电影级联合重采样与圆锥坐标保障推断严谨")

    pipe_cards = [
        (
            "Step 1｜版面去噪裁剪", C_NAVY,
            "切除底部 12% 演职员区",
            "电影海报底部密集排布白/黑演职员小字（Billing Block）、发行商徽标与分级标。统一裁除底部 12% 后缩放至 120×160，消除文字墨迹对背景底色的固定拉偏。",
        ),
        (
            "Step 2｜全幅连续视觉指标", C_BLUE,
            "保留全部 N = 19,694 张",
            "在全幅画面提取平均明度 mean_v、平均饱和度 mean_s、明暗对比度 v_std，以及 Hasler–Süsstrunk 色彩丰富度：\ncolorful = √(σ_rg²+σ_yb²) + 0.3√(μ_rg²+μ_yb²)。",
        ),
        (
            "Step 3｜近灰像素掩膜（核心亮点）", C_ORANGE,
            "定义掩膜 mask = (S ≥ 0.20)",
            "黑白灰像素（S → 0）的色相角 H 完全由 JPEG 量化噪声随机支配，直接统计会将主色拉向纯黑并污染色相直方图。仅在掩膜内有色像素上统计 12 扇区 h0–h11 与前三大主色。",
        ),
        (
            "Step 4｜色相质量闸门与等权聚合", C_GREEN,
            "sat_frac ≥ 0.10（N = 19,072）",
            "排除有色像素不足 10% 的 622 张近纯黑白灰海报；先在单张海报内归一化 ∑h_i = 1，再对组内电影等权平均（一片一票），杜绝高饱和大片垄断组均值。",
        ),
    ]
    for idx, (p_tag, p_col, p_kpi, p_desc) in enumerate(pipe_cards):
        px = 0.50 + idx * 3.12
        add_box(s5, px, 1.18, 2.97, 3.05, fill=C_WHITE, border=C_BORDER, border_pt=0.8)
        add_box(s5, px, 1.18, 2.97, 0.08, fill=p_col, border=None)
        tb_p = s5.shapes.add_textbox(Inches(px + 0.12), Inches(1.32), Inches(2.73), Inches(2.80))
        tf_p = tb_p.text_frame
        tf_p.word_wrap = True
        add_rich_paragraph(tf_p, [(p_tag, 9.6, True, p_col, "cn")], first=True, space_after=3)
        add_rich_paragraph(tf_p, [(p_kpi, 11.8, True, C_DARK, "cn")], space_after=6)
        add_rich_paragraph(tf_p, [(p_desc, 9.2, False, C_TEXT, "cn")], space_after=0, line_spacing=1.28)

    # 下排两张核心统计建模卡片
    add_metric_card(
        s5, 0.50, 4.44, 6.05, 2.50, C_NAVY,
        "统计推断设计｜解决多标签重叠计数难题",
        "整库电影级联合 Bootstrap（1,000 次）+ 互斥子集检验",
        [
            "一部电影常含 1–3 个类型标签（如科幻与恐怖重叠 588 部），直接拼列联表做常规卡方检验会违反观测独立性假设。",
            "对 19,694 部独立电影有放回整库抽样，在同一次重抽样本上同步计算两类型差值，精确保留重叠影片协方差。",
            "同步在剔除重叠后的 N = 6,840 严格互斥三类子集上计算 Kruskal–Wallis H 与效应量 η²_H，双重锁定显著性。",
        ],
        kpi_pt=13.0, body_pt=9.4,
    )
    add_metric_card(
        s5, 6.78, 4.44, 6.05, 2.50, C_ORANGE,
        "无监督建模设计｜解决色相周期断层与低饱和权重膨胀",
        "五维圆锥色度空间 Conic_5D = [V, S, C, S·cosH, S·sinH]",
        [
            "色相角满足 0° ≡ 360° 环形拓扑；若单独将 cosH、sinH 标准化，低饱和灰海报与高纯海报会获得相同色相欧氏距离。",
            "用 mean_s 加权色相单位向量构造 HSV 圆锥横截面坐标，使低饱和海报自然向圆锥轴心靠拢。",
            "横跨 3 种特征空间 × 3 类算法（K-Means / Bisecting K-Means / GMM）× k∈{2..6} 共 45 组实验客观择优。",
        ],
        kpi_pt=13.0, body_pt=9.4,
    )

    # =========================================================================
    # Slide 6: 发现一（结构 · 做法 A）：预设类型的明度阶梯与冷暖分野
    # =========================================================================
    s6 = prs.slides.add_slide(blank)
    apply_slide_chrome(s6, 6, "05 · 结构维度（做法 A）", "预设类型对比：明度是区分类型最强指标（效应量 η² = 0.219），爱情暖红、科幻青蓝分野清晰")

    add_fitted_picture(s6, ROOT / "outputs" / "b" / "ppt" / "fig_q1_genre_hue.png", 0.50, 1.16, 6.06, 3.56, with_card=True, pad=0.06)
    add_fitted_picture(s6, ROOT / "outputs" / "b" / "ppt" / "fig_q1_genre_metrics.png", 6.77, 1.16, 6.06, 3.56, with_card=True, pad=0.06)

    s6_cards = [
        (
            0.50, C_NAVY, "明度拉开 0.226 清晰梯度",
            "爱情较恐怖高 +0.1990 [+0.1902, +0.2078]",
            ["喜剧(0.631)、动画(0.608)、爱情(0.603)显著偏亮；科幻(0.484)、惊悚(0.440)、恐怖(0.404)依次偏暗；互斥子集 KW H = 1501.1。"],
        ),
        (
            4.68, C_ORANGE, "12 扇区色相波段精准错位",
            "爱情暖色 +14.83pp · 科幻青蓝 +11.09pp",
            ["爱情 0°–60° 红橙黄达 54.18%；科幻与动画 180°–240° 青蓝达 32.48% / 32.14%；恐怖 90°–150° 绿调较爱情高 +1.73pp。"],
        ),
        (
            8.86, C_BLUE, "浅底柔光 vs 高纯度涂抹",
            "动画丰富度居首 (79.80) · 爱情饱和度最低 (0.381)",
            ["爱情虽高明度高暖色，但平均饱和度低于科幻(0.442)与恐怖(0.430)，体现大量爱情片采用浅白柔光底色而非浓烈涂抹。"],
        ),
    ]
    for sx, scol, stag, skpi, sbul in s6_cards:
        add_metric_card(s6, sx, 4.88, 3.97, 2.06, scol, stag, skpi, sbul, kpi_pt=11.8, body_pt=9.2)

    # =========================================================================
    # Slide 7: 发现一（结构 · 做法 B）：无监督四类客观色型与典型海报色卡
    # =========================================================================
    s7 = prs.slides.add_slide(blank)
    apply_slide_chrome(s7, 7, "06 · 结构维度（做法 B）", "无监督色型聚类：数据自动收敛出四类基础色型（k=4, ARI=0.991），各类型按比例调配模板")

    add_fitted_picture(s7, ROOT / "outputs" / "b" / "ppt" / "fig_q1_cluster.png", 0.50, 1.16, 6.20, 3.60, with_card=True, pad=0.06)
    add_fitted_picture(s7, ROOT / "outputs" / "b" / "ppt" / "fig_q1_palettes.png", 6.88, 1.16, 5.95, 3.60, with_card=True, pad=0.06)

    arch_cards = [
        (0.50, C_GOLD, "明亮浅调｜28.65% (5,464 部)", "V=0.713 · S=0.253", ["爱情 41.1%(+12.4pp)、喜剧 39.6%(+11.0pp) 高度集中；恐怖仅 11.9%。"]),
        (3.62, C_ORANGE, "浓烈暖调｜25.93% (4,946 部)", "S=0.576 · 暖色 68.1%", ["全库丰富度最高(92.1)；动画 32.9%、动作 29.2%、喜剧 28.5% 突出。"]),
        (6.74, C_BLUE, "青蓝冷调｜19.42% (3,704 部)", "S=0.537 · 青蓝 57.8%", ["动画 35.9%(+16.5pp)、科幻 30.8%(+11.4pp) 显著富集，冷调特征鲜明。"]),
        (9.86, C_SLATE, "深暗低彩｜25.99% (4,958 部)", "V=0.330 · C=38.7", ["恐怖 42.1%(+16.1pp)、惊悚 40.3%、犯罪 34.3% 以此为主导视觉模板。"]),
    ]
    for ax, acol, atag, akpi, abul in arch_cards:
        add_metric_card(s7, ax, 4.92, 2.97, 2.02, acol, atag, akpi, abul, kpi_pt=11.6, body_pt=8.9)

    # =========================================================================
    # Slide 8: 发现二（时间 · 图 2）：1950—2025 年全球海报配色的长期演变
    # =========================================================================
    s8 = prs.slides.add_slide(blank)
    apply_slide_chrome(s8, 8, "07 · 时间维度（图 2）", "1950—2025 年演变：整体变暗（−0.0705）且青蓝扩张，但 2020 年后饱和度显著反弹（+0.0424）")

    add_fitted_picture(s8, ROOT / "outputs" / "c" / "ppt" / "fig_q2_hue.png", 0.50, 1.16, 6.06, 3.56, with_card=True, pad=0.06)
    add_fitted_picture(s8, ROOT / "outputs" / "c" / "ppt" / "fig_q2_metrics.png", 6.77, 1.16, 6.06, 3.56, with_card=True, pad=0.06)

    s8_cards = [
        (
            0.50, C_NAVY, "完整十年对比（2010s − 1950s）",
            "明度 −0.0705 · 丰富度 −16.88",
            ["95% CI 分别为 [−0.0835, −0.0588] 与 [−19.33, −14.57]；76 年年度中位数 Spearman ρ 达 −0.752 与 −0.804。"],
        ),
        (
            4.68, C_BLUE, "色相结构由红黄向青蓝迁移",
            "暖色 −10.8pp · 青蓝 +10.3pp",
            ["1950s 手绘海报 0°–60° 暖色占 58.6%、青蓝仅 17.4%；至 2010s 暖色降至 47.8%，180°–240° 青蓝升至 27.7%。"],
        ),
        (
            8.86, C_ORANGE, "饱和度非单调，否定「一路变灰」",
            "2020–2025 较 2010s 饱和度 +0.0424",
            ["95% CI [+0.0347, +0.0507]：流媒体缩略图环境在压低背景明度(−0.0364)的同时强化了高纯色彩对比（右图阴影为片间 IQR）。"],
        ),
    ]
    for sx, scol, stag, skpi, sbul in s8_cards:
        add_metric_card(s8, sx, 4.88, 3.97, 2.06, scol, stag, skpi, sbul, kpi_pt=11.8, body_pt=9.1)

    # =========================================================================
    # Slide 9: 发现三（效用 · 图 3）：配色不预测口碑——显著性与效应量解耦
    # =========================================================================
    s9 = prs.slides.add_slide(blank)
    apply_slide_chrome(s9, 9, "08 · 效用维度（图 3）", "口碑预测力检验：全部相关系数落在 ±0.08 以内（R² < 0.3%），配色传达题材而非影片质量")

    add_fitted_picture(s9, ROOT / "figures" / "fig_q3_score.png", 0.50, 1.16, 12.33, 3.78, with_card=True, pad=0.07)

    add_metric_card(
        s9, 0.50, 5.10, 6.05, 1.86, C_RED,
        "定量检验结果｜N = 19,592 部有效评分电影（全库 + 八大类型）",
        "明度 r = +0.047 · 饱和度 r = −0.052 · 丰富度 r = −0.045",
        [
            "线性拟合斜率仅为 +0.19：即使海报从纯黑（0）变到纯白（1），TMDB 均分平均仅波动 0.19 分。",
            "分八大类型考察，相关系数分布在 −0.079（爱情）至 +0.055（惊悚）之间，全部紧贴 0 轴虚线。",
        ],
        kpi_pt=12.8, body_pt=9.3,
    )
    add_metric_card(
        s9, 6.78, 5.10, 6.05, 1.86, C_NAVY,
        "统计学与业务启示｜警惕大样本下的「p 值显著性幻觉」",
        "p < 10⁻¹⁰ ≠ 实质相关：必须以效应量（r / R²）作为判断基准",
        [
            "当样本量达 1.96 万部时，极微弱噪音也会产生极小 p 值，但决定系数 R² 不足千分之三，毫无预测价值。",
            "核心定性结论：海报配色的工业职能是降低观众搜寻成本、快速提示「这是什么类型」，而非区分佳作与烂片。",
        ],
        kpi_pt=12.8, body_pt=9.3,
    )

    # =========================================================================
    # Slide 10: 发现四（空间 · 图 4）：2001—2025 年七大国家／地区组配色差异
    # =========================================================================
    s10 = prs.slides.add_slide(blank)
    apply_slide_chrome(s10, 10, "09 · 空间维度（图 4）", "2001—2025 年地区对比：法意日偏亮且日本暖色最低（37.5%），华语与韩国显著偏暗冷")

    add_fitted_picture(s10, ROOT / "outputs" / "c" / "ppt" / "fig_q4_hue.png", 0.50, 1.16, 6.06, 3.56, with_card=True, pad=0.06)
    add_fitted_picture(s10, ROOT / "outputs" / "c" / "ppt" / "fig_q4_metrics.png", 6.77, 1.16, 6.06, 3.56, with_card=True, pad=0.06)

    s10_cards = [
        (
            0.50, C_NAVY, "唯一归属口径（10,115 部）",
            "制片国 + 原语言去重 · 美国为参照系",
            ["限定 2001—2025 同代窗口；陆港台合为华语组(ZH)，多国合拍匹配原语言母国，歧义片仅 2.99% 单列剔除。"],
        ),
        (
            4.68, C_GREEN, "明暗与饱和度的区域分野",
            "法(+0.060) 意(+0.072) 亮 · 韩饱和度 −0.103",
            ["法、意、日(+0.047)较美国(0.519)显著偏亮；华语(−0.051)与韩国(−0.077)偏暗，韩国丰富度低出 22.41。"],
        ),
        (
            8.86, C_BLUE, "日本高青蓝特征与解释边界",
            "日本 0°–60° 暖色 37.5% vs 美国 48.4%",
            ["日本 180°–240° 青蓝达 33.0%，契合动画与青春奇幻片高占比；韩国冷暗契合犯罪惊悚外输片结构，不做文化因果推断。"],
        ),
    ]
    for sx, scol, stag, skpi, sbul in s10_cards:
        add_metric_card(s10, sx, 4.88, 3.97, 2.06, scol, stag, skpi, sbul, kpi_pt=11.6, body_pt=9.1)

    # =========================================================================
    # Slide 11: 稳健性核验与五大研究局限（Threats to Validity）
    # =========================================================================
    s11 = prs.slides.add_slide(blank)
    apply_slide_chrome(s11, 11, "10 · 稳健性与研究局限", "严谨性闭环：三项超参数与肤色屏蔽检验全部稳健，五方面界定结论适用边界")

    # 左栏：附录对比敏感性图 + 核验摘要卡
    add_fitted_picture(s11, ROOT / "figures" / "b" / "fig_q1_comparisons.png", 0.50, 1.16, 5.95, 3.82, with_card=True, pad=0.06)
    add_metric_card(
        s11, 0.50, 5.10, 5.95, 1.86, C_GREEN,
        "三项敏感性核验（全部通过）",
        "剔除肤色干扰、扫描过滤阈值、剥离多标签重叠后结论一致",
        [
            "屏蔽 0°–60° 肤色区重归一：科幻青蓝(46.8%)仍显著高于爱情(39.9%, +6.93pp)与恐怖(35.2%)。",
            "sat_frac 在 0.05–0.20 连续扫描：波段差值波动 < 0.3pp，四类色型重聚类 ARI 保持 0.915–0.979。",
            "严格互斥三类子集（N = 6,840）：剔除重叠影片后，明度 KW H = 1501.1（效应量 η² = 0.2193）完全稳健。",
        ],
        kpi_pt=11.4, body_pt=8.7,
    )

    # 右栏：五大研究局限卡片列表
    limits = [
        ("局限 1｜内部有效性：电影上映年 ≠ 海报设计年", "TMDB 无海报发行日期字段；老片原语言池仍可能含近年蓝光修复或重映版海报，部分稀释历史真实差幅。", C_ORANGE),
        ("局限 2｜内部有效性：印制媒介演进与审美迁移混杂", "1950s 石版手绘插画纸面留白多，2000s 后转向数字暗房合成与小屏缩略图，明度下降不能单一归因于审美变暗。", C_NAVY),
        ("局限 3｜结构有效性：推定国家组 ≠ 民族文化因果", "多国合拍依赖规则推定，且未剥离各国入库片种构成差异（如韩国犯罪惊悚占比高），仅作样本客观描述。", C_BLUE),
        ("局限 4｜结构有效性：整幅像素聚合未分离前景与背景", "当前指标对裁去底部 12% 后的画面整体统计，尚未区分「大面积纯黑底 + 局部霓虹高亮」与「整幅均匀灰暗」。", C_SLATE),
        ("局限 5｜外部有效性：平台覆盖偏倚与近期新片右删失", "TMDB 投票群体以欧美观众为主；2020—2025 年未满完整十年且新片投票仍在累积，近期截面需谨慎外推。", C_RED),
    ]
    for idx, (l_hd, l_bd, l_col) in enumerate(limits):
        ly = 1.16 + idx * 1.18
        add_box(s11, 6.65, ly, 6.18, 1.08, fill=C_WHITE, border=C_BORDER, border_pt=0.75)
        add_box(s11, 6.65, ly, 0.07, 1.08, fill=l_col, border=None)
        add_textbox(
            s11, 6.80, ly + 0.06, 5.95, 0.96,
            [(l_hd, 10.2, True, l_col), (l_bd, 9.0, False, C_TEXT)],
            line_spacing=1.20, pad_lr=0.02, pad_tb=0.0,
        )

    # =========================================================================
    # Slide 12: 总结、全组模块分工与可复现流水线（Q&A）
    # =========================================================================
    s12 = prs.slides.add_slide(blank)
    apply_slide_chrome(s12, 12, "11 · 总结与分工 Q&A", "全组协同与可复现工程：data/ 只读契约、百余项自动化断言核验与一键确定性复现")

    # 顶部三栏综合认知条
    syn_items = [
        ("横向看（结构 × 空间）", "全行业共享四类基础色型模板，类型与地区通过调整模板配比形成稳定的视觉预期。", C_ORANGE),
        ("纵向看（76 年时间演变）", "背景明度长期下探、青蓝扩张，但流媒体时代局部高饱和回弹，并非线性变灰。", C_BLUE),
        ("效用看（口碑预测边界）", "配色与评分相关近零（|r|<0.08）：色彩解决「题材分类定位」，不决定「作品质量高低」。", C_GREEN),
    ]
    for idx, (shd, sbd, scol) in enumerate(syn_items):
        sx = 0.50 + idx * 4.18
        add_box(s12, sx, 1.16, 3.97, 1.04, fill=C_WHITE, border=scol, border_pt=1.0, rounded=True)
        add_textbox(
            s12, sx + 0.12, 1.22, 3.73, 0.90,
            [(shd, 10.4, True, scol), (sbd, 9.0, False, C_TEXT)],
            line_spacing=1.22, pad_lr=0.02, pad_tb=0.0,
        )

    # 中部：全组四模块交付矩阵表
    tbl_s12 = s12.shapes.add_table(5, 4, Inches(0.50), Inches(2.36), Inches(12.33), Inches(3.12))
    rows_s12 = [
        ["角色模块", "核心职责与方法贡献", "关键代码与数据产物", "自动化质量核验闭环"],
        ["成员 A\n数据基建与图 3", "动态 2.6% 分位采样、8,000 张海报去本地化、底部裁剪 + 近灰掩膜特征提取、口碑回归检验", "scripts/01_fetch..06_details.py\ndata/*.csv · figures/fig_q3_score.png", "data/quality_report.md\nGit pre-commit 只读锁保护"],
        ["成员 B\n结构对比与色型聚类", "9 类与主讲 3 类联合 Bootstrap、45 组圆锥色度无监督聚类(k=4)、14×10 抽象色卡、肤色屏蔽核验", "outputs/b/scripts/b01..b99\nfigures/b/fig_q1_*.png · outputs/b/ppt/", "b99_validate.py\n36 / 36 项检查全通过"],
        ["成员 C\n时间演变与跨国对比", "76 年 5 年移动窗口轨迹、制片国+原语言唯一归属(10,115 部)、年代与七国 Bootstrap 均值差及色卡", "outputs/c/scripts/c01..c99\nfigures/c/fig_q2_*, fig_q4_*.png", "c99_validate.py\n70 / 70 项检查全通过"],
        ["成员 D\n视觉统稿与汇报交付", "全组图表规范对齐、九节万字课程报告统稿（Markdown + Word 三线表）、12 页宽屏 PPT 与讲稿", "outputs/d/scripts/d01..d99\ndocs/报告.md & .docx · docs/汇报.pptx", "d99_validate.py\n文档/图表/零泄漏全量核验"],
    ]
    for r_i, r_vals in enumerate(rows_s12):
        for c_i, val in enumerate(r_vals):
            tbl_s12.table.cell(r_i, c_i).text = val
    style_ppt_table(
        tbl_s12.table,
        [1.85, 4.55, 3.38, 2.55],
        [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER],
        body_font_pt=9.0, head_font_pt=9.8,
    )

    # 底部：离线复现命令卡 + Q&A 致谢卡
    add_box(s12, 0.50, 5.64, 8.15, 1.32, fill=C_WHITE, border=C_BORDER, border_pt=0.8)
    tb_cmd = s12.shapes.add_textbox(Inches(0.64), Inches(5.70), Inches(7.88), Inches(1.20))
    tf_cmd = tb_cmd.text_frame
    tf_cmd.word_wrap = True
    add_rich_paragraph(tf_cmd, [("离线确定性一键复现流水线（无需 API Key / 无需重下 1.5GB 原图，SHA-256 锁定输入）：", 9.6, True, C_NAVY, "cn")], first=True, space_after=3)
    add_rich_paragraph(
        tf_cmd,
        [(
            "python scripts/04_yearly.py  &&  python scripts/05_fig3_score.py\n"
            "python outputs/b/scripts/b01_genre.py .. b99_validate.py   # 结构与聚类 + 36 项核验\n"
            "python outputs/c/scripts/c01_country_group.py .. c99_validate.py  &&  python outputs/d/scripts/d01..d99",
            8.6, False, C_DARK, "mono",
        )],
        space_after=0, line_spacing=1.22,
    )

    add_box(s12, 8.85, 5.64, 3.98, 1.32, fill=C_NAVY, border=None, rounded=True)
    add_textbox(
        s12, 9.00, 5.76, 3.68, 1.08,
        [
            ("感谢聆听 · 敬请批评指正", 15.5, True, C_WHITE),
            ("Questions & Discussion", 11.0, False, RGBColor(253, 186, 116)),
        ],
        line_spacing=1.28, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
    )

    # 写入每页演讲者备注（Speaker Notes）
    for idx, slide in enumerate(prs.slides):
        ns = slide.notes_slide
        ntf = ns.notes_text_frame
        ntf.text = f"【{SPEAKER_NOTES[idx][0]}】\n{SPEAKER_NOTES[idx][1]}"


def write_companion_markdown() -> None:
    md_lines = [
        "# 《海报会说话》12 页课程汇报大纲与逐页讲稿",
        "",
        "> **配套演示文稿**：`docs/汇报.pptx`（16:9 宽屏，共 12 页，已内嵌演讲者备注）  ",
        "> **建议汇报时长**：10—12 分钟（平均每页约 50—60 秒）",
        "",
        "---",
        "",
        "## 一、 12 页幻灯片结构与时间分配总表",
        "",
        "| 页码 | 章节定位 | 页面核心结论标题 | 嵌入核心图表／组件 | 建议用时 |",
        "| :---: | --- | --- | --- | :---: |",
        "| 01 | 封面 | 海报会说话——电影海报配色的类型结构、时间演变与地区差异 | `figures/b/fig_q1_palettes.png` | 0:30 |",
        "| 02 | 总纲 | 一句话总纲：配色是识别题材的「类型信号」，随时代地区迁移，但不预测口碑 | 四维核心定量卡片矩阵 | 1:00 |",
        "| 03 | 框架 | 将行业经验直觉拆解为四个正交实证维度，统一以「单部电影」为统计单元 | 直觉证伪卡 + 四维设计矩阵表 | 0:50 |",
        "| 04 | 数据 | 用「每年票数前 2.6%」消除幸存者偏差，替换 8,000 张本地化海报 | `poster_lang_effect.png` + `v1_vs_v2.png` | 1:10 |",
        "| 05 | 方法 | 用 S ≥ 0.20 近灰掩膜剥离压缩噪声，以联合重采样与圆锥坐标保障严谨 | 四步特征流水线 + 统计建模双卡 | 1:00 |",
        "| 06 | 图 1A | 预设类型对比：明度是区分类型最强指标（效应量 η² = 0.219），冷暖分野清晰 | `fig_q1_genre_hue.png` + `fig_q1_genre_metrics.png` | 1:10 |",
        "| 07 | 图 1B | 无监督聚类：自动收敛四类共享色型（k=4, ARI=0.991），各类型按比例配比 | `fig_q1_cluster.png` + `fig_q1_palettes.png` | 1:15 |",
        "| 08 | 图 2 | 1950—2025 年演变：整体变暗且青蓝扩张，但近期饱和度显著反弹（+0.0424） | `fig_q2_hue.png` + `fig_q2_metrics.png` | 1:05 |",
        "| 09 | 图 3 | 口碑预测力检验：全部相关系数落在 ±0.08 以内（R² < 0.3%），区分显著性与效应量 | `figures/fig_q3_score.png` | 0:55 |",
        "| 10 | 图 4 | 2001—2025 年地区对比：法意日偏亮（日本暖色 37.5%），韩华偏暗冷 | `fig_q4_hue.png` + `fig_q4_metrics.png` | 1:05 |",
        "| 11 | 稳健与局限 | 三项超参数与肤色屏蔽检验全部稳健，五方面界定结论适用边界 | `figures/b/fig_q1_comparisons.png` + 五大局限卡 | 1:00 |",
        "| 12 | 总结与 Q&A | 只读数据契约、百余项自动化断言核验与一键确定性复现 | A/B/C/D 交付矩阵表 + 复现命令链 | 0:45 |",
        "",
        "---",
        "",
        "## 二、 逐页口头汇报讲稿（可直接用于预演）",
        "",
    ]
    for title, script in SPEAKER_NOTES:
        md_lines.append(f"### {title}")
        md_lines.append("")
        md_lines.append(script)
        md_lines.append("")

    md_lines.extend([
        "---",
        "",
        "## 三、 答辩高频提问预案（Q&A 备询卡）",
        "",
        "1. **问：所有类型在 0°–60° 红橙黄占比都很高，是不是仅仅因为海报上有人脸肤色？**  ",
        "   **答**：我们在附录图 A1 专门做了**单张海报内屏蔽 `h0`、`h1`（0°–60°）并对剩余 60°–360° 重新归一化**的敏感性实验：剔除红橙黄肤色高发区后，科幻片在 180°–240° 青蓝波段占比（46.82%）依然显著高于爱情片（39.89%，差值 +6.93pp，95% CI [+5.06, +8.82]）与恐怖片（35.19%），证明冷暖分化并非单纯由人脸面积差异造成。",
        "",
        "2. **问：无监督聚类为什么聚出 4 类而不是 3 类或 19 类？轮廓系数 0.2675 算不算低？**  ",
        "   **答**：电影海报色彩本身分布在连续渐变的圆锥流形上，不存在人工玩具数据集那样的真空断层，因此 0.27 左右的轮廓系数符合连续图像特征常态；更重要的是，在 80% 无放回子样本重训下，4 类划分的调整兰德指数高达 **ARI = 0.9913**，说明这四个分割边界极其稳定。它揭示的真实机制是「全行业共享四套色型模板，不同题材调整模板配比」。",
        "",
        "3. **问：韩国组平均明度和饱和度最低、日本组暖色最低，能不能说东亚审美更冷暗？**  ",
        "   **答**：不能直接上升为民族文化心理因果推断。我们在空间比较中刻意保留了各国入库热门片的真实题材构成：TMDB 高票韩国片中犯罪、惊悚题材占比显著高于法国与意大利，而日本高票片中动画与青春奇幻占比较高。组间差异首先反映的是各国在国际主流视野中优势输出片种的结构差异。",
        "",
        "4. **问：图 2 右侧曲线的灰色阴影和图 4 右侧横线分别代表什么？**  ",
        "   **答**：两者统计含义严格区分——图 2 右侧阴影是五年移动窗口内的**片间四分位距（IQR，25%—75% 分位数）**，用来展示同一时期电影海报内部的多样性跨度；图 4 右侧横线则是组均值的**逐项 95% Bootstrap 置信区间**，用来刻画均值估计的不确定性。",
        "",
    ])
    DST_MD.write_text("\n".join(md_lines), encoding="utf-8")


def main() -> None:
    import shutil
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    build_slides(prs)
    DST_PPTX.parent.mkdir(parents=True, exist_ok=True)
    COPY_D_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(DST_PPTX))
    write_companion_markdown()
    shutil.copy2(DST_PPTX, COPY_D_PPTX)
    shutil.copy2(DST_MD, COPY_D_MD)
    shutil.copy2(DST_PPTX, OUTER_PPTX)
    print(f"PPT 已生成：{DST_PPTX}（共 {len(prs.slides)} 页，已同步至 {COPY_D_PPTX} 与 {OUTER_PPTX}）")
    print(f"配套讲稿已生成：{DST_MD}（已同步至 {COPY_D_MD}）")


if __name__ == "__main__":
    main()
