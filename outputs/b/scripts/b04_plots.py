"""绘制 B 组出版级报告定稿图（300 DPI）与 16:9 PPT 汇报图面（150 DPI）。"""
import colorsys
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.stats import gaussian_kde

from b_common import (
    CLUSTER_IDS,
    CLUSTER_NAMES,
    FIG_B,
    GENRE_COLOR,
    HUE_COLORS,
    MAIN_GENRES,
    METRIC_LABELS,
    METRICS,
    PPT_DIR,
    PRESET_GENRES,
    ROOT,
    SEED,
    TABLES,
    apply_plot_rc,
    common,
    load_safe,
)

# refined 4-archetype editorial palette
ARCHETYPE_COLORS = {
    0: "#dce4ec",  # 明亮浅调：柔和象牙浅灰蓝
    1: "#d95f2b",  # 浓烈暖调：陶土朱砂暖橙
    2: "#1d6fa5",  # 青蓝冷调：深海钴青蓝
    3: "#1e293b",  # 深暗低彩：午夜深炭灰
}

SHORT_SECTORS = [
    "0–30°\n红", "30–60°\n橙黄", "60–90°", "90–120°",
    "120–150°\n绿", "150–180°", "180–210°\n青", "210–240°\n蓝",
    "240–270°", "270–300°\n紫", "300–330°", "330–360°",
]

COMPACT_SECTORS = [
    "0°\n红", "30°", "60°\n黄", "90°",
    "120°\n绿", "150°", "180°\n青", "210°",
    "240°\n蓝", "270°", "300°\n紫", "330°",
]


def hex_to_rgb01(h: object) -> np.ndarray | None:
    if isinstance(h, str) and len(h) == 7 and h.startswith("#"):
        try:
            return np.array([int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)], dtype=float) / 255.0
        except ValueError:
            return None
    return None


def blended_poster_colors(df_sub: pd.DataFrame) -> np.ndarray:
    """融合每张海报的 3 个主色（按 ds1..ds3 面积加权）并做轻度伽马提亮，真实展现整幅海报色调。"""
    out = np.zeros((len(df_sub), 3), dtype=float)
    for idx, r in enumerate(df_sub.itertuples()):
        acc = np.zeros(3, dtype=float)
        wsum = 0.0
        for k in (1, 2, 3):
            rgb = hex_to_rgb01(getattr(r, f"dom{k}", None))
            w = float(getattr(r, f"ds{k}", 0.0) or 0.0)
            if rgb is not None and w > 0:
                acc += rgb * w
                wsum += w
        if wsum > 0:
            c = np.clip(acc / wsum, 0.0, 1.0) ** 0.86
        else:
            c = np.array(colorsys.hsv_to_rgb(float(r.hue) / 360.0, float(r.mean_s), float(r.mean_v)))
        out[idx] = c
    return out


def draw_hue_bars(
    ax: plt.Axes,
    hue_df: pd.DataFrame,
    row_labels: list[str],
    show_legend: bool = True,
    show_summary_col: bool = False,
    font_scale: float = 1.0,
) -> None:
    """绘制带细白分割线的 12 扇区 100% 堆叠色相条，可选右侧冷暖摘要列。"""
    y = np.arange(len(hue_df))
    left = np.zeros(len(hue_df), dtype=float)
    for i, col_rgb in enumerate(HUE_COLORS):
        vals = np.where(hue_df["n_hue"].to_numpy() >= 30, hue_df[f"h{i}"].to_numpy(dtype=float) * 100.0, 0.0)
        ax.barh(y, vals, left=left, color=col_rgb, height=0.68, edgecolor="white", linewidth=0.45)
        left += vals

    if show_summary_col:
        for row_i, r in enumerate(hue_df.itertuples()):
            w_pct = float(r.warm_0_60) * 100.0
            c_pct = float(r.cool_180_240) * 100.0
            ax.text(
                101.6, row_i,
                f"暖 {w_pct:4.1f}% · 青蓝 {c_pct:4.1f}%",
                va="center", ha="left",
                fontsize=8.6 * font_scale,
                color="#475569",
            )
        ax.set_xlim(0, 123)
        ax.spines["bottom"].set_bounds(0, 100)
    else:
        ax.set_xlim(0, 100)

    ax.set_yticks(y, row_labels)
    ax.invert_yaxis()
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("平均色相占比（%）")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#94a3b8")
    ax.tick_params(axis="y", length=0)
    if show_legend:
        ax.legend(
            [Patch(facecolor=HUE_COLORS[i], edgecolor="none") for i in [0, 1, 4, 6, 7, 9]],
            ["红 (0°)", "橙黄 (60°)", "绿 (120°)", "青 (180°)", "蓝 (240°)", "紫 (300°)"],
            loc="lower center",
            bbox_to_anchor=(0.43 if show_summary_col else 0.5, 1.00),
            ncol=6,
            frameon=False,
            fontsize=8.8 * font_scale,
        )


def draw_preset_sector_bars(ax: plt.Axes, hue_df: pd.DataFrame, compact_ppt: bool = False) -> None:
    """绘制科幻、爱情、恐怖 12 扇区并排柱状图 + 底部连续 360° 光谱色带 + 关键峰值微标。"""
    sub = hue_df.set_index("group").loc[PRESET_GENRES]
    x = np.arange(12)
    width = 0.255
    offsets = [-width, 0.0, width]

    bars_by_genre = {}
    for off, g in zip(offsets, PRESET_GENRES):
        vals = [float(sub.loc[g, f"h{i}"]) * 100.0 for i in range(12)]
        n_h = int(sub.loc[g, "n_hue"])
        rects = ax.bar(
            x + off,
            vals,
            width=width,
            color=GENRE_COLOR[g],
            alpha=0.92,
            edgecolor="white",
            lw=0.7,
            label=f"{g}（有效色相 n={n_h:,}）",
            zorder=3,
        )
        bars_by_genre[g] = (x + off, vals, rects)

    # 关键代表峰值直接标出干净数字（无边框口号，纯数字微标）
    peak_specs = [
        ("爱情", 0, 0.8),
        ("科幻", 6, 0.8),
        ("科幻", 7, 0.8),
        ("恐怖", 4, 0.8),
    ]
    fs_num = 10.5 if compact_ppt else 8.2
    for g, sec_idx, dy in peak_specs:
        xs_g, vals_g, _ = bars_by_genre[g]
        ax.text(
            xs_g[sec_idx], vals_g[sec_idx] + dy,
            f"{vals_g[sec_idx]:.1f}%",
            ha="center", va="bottom",
            fontsize=fs_num, fontweight="bold", color=GENRE_COLOR[g],
        )

    # 底部连续 360° 光谱渐变条（0°..360° 对应 x = -0.5..11.5）
    grad_rgb = np.array([[colorsys.hsv_to_rgb(d / 360.0, 0.72, 0.90) for d in range(360)]], dtype=float)
    ax.imshow(
        grad_rgb,
        extent=[-0.48, 11.48, -2.3, -0.7],
        aspect="auto",
        interpolation="bicubic",
        zorder=4,
        clip_on=False,
    )

    ax.set_xticks(x, COMPACT_SECTORS if compact_ppt else SHORT_SECTORS)
    if compact_ppt:
        ax.set_xlabel("色相扇区起点角度（每格宽 30°）")
    ax.set_xlim(-0.55, 11.55)
    ax.set_ylim(-2.6, 43.0)
    ax.set_yticks([0, 10, 20, 30, 40])
    ax.set_ylabel("平均色相占比（%）")
    ax.grid(axis="y", color="#e2e8f0", lw=0.8, zorder=1)
    ax.spines["bottom"].set_color("#94a3b8")
    ax.spines["left"].set_color("#94a3b8")
    ax.legend(
        loc="upper right",
        frameon=False,
        ncol=1 if compact_ppt else 3,
        fontsize="small",
    )


def draw_genre_halfeye_forest(
    ax: plt.Axes,
    raw_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    metric: str,
    show_ylabels: bool = True,
    font_scale: float = 1.0,
) -> None:
    """绘制 Nature/ggdist 风格半眼图（Half-Eye）：背景交替导视条 + 影片分布核密度柔影 + 组均值及 95% CI + 右侧均值读数。"""
    s_main = summary_df.set_index("genre").loc[MAIN_GENRES]
    all_mean = float(summary_df.set_index("genre").loc["ALL", f"{metric}_mean"])

    # 设定统一横轴范围以容纳全片核密度柔影与右侧数值列
    if metric == "mean_v":
        x_lo, x_hi, x_text = 0.22, 0.88, 0.865
        xticks = [0.3, 0.5, 0.7]
        fmt_str = "{:.2f}"
    elif metric == "mean_s":
        x_lo, x_hi, x_text = 0.15, 0.77, 0.755
        xticks = [0.2, 0.4, 0.6]
        fmt_str = "{:.2f}"
    else:
        x_lo, x_hi, x_text = 20.0, 130.0, 127.5
        xticks = [30, 60, 90]
        fmt_str = "{:.1f}"

    y = np.arange(len(MAIN_GENRES))
    for i, g in enumerate(MAIN_GENRES):
        if i % 2 == 1:
            ax.axhspan(i - 0.46, i + 0.46, facecolor="#f4f7fa", edgecolor="none", zorder=0)

        vals = raw_df.loc[common.has_genre(raw_df, g), metric].to_numpy(dtype=float)
        p10, p90 = np.percentile(vals, [10, 90])
        grid_x = np.linspace(p10, p90, 80)
        kde = gaussian_kde(vals, bw_method=0.28)
        dens = kde(grid_x)
        dens = (dens / dens.max()) * 0.36

        col = GENRE_COLOR[g] if g in PRESET_GENRES else "#335c7d"
        base_y = i + 0.14
        # y 轴反转后向上生长即数值减小方向 (base_y - dens)
        ax.fill_between(grid_x, base_y - dens, base_y, color=col, alpha=0.17, edgecolor="none", zorder=2)
        ax.plot(grid_x, base_y - dens, color=col, lw=0.75, alpha=0.45, zorder=2)

        q1, q3 = float(s_main.loc[g, f"{metric}_q1"]), float(s_main.loc[g, f"{metric}_q3"])
        ax.plot([q1, q3], [base_y, base_y], color=col, lw=2.2, alpha=0.32, solid_capstyle="round", zorder=3)

        m_val = float(s_main.loc[g, f"{metric}_mean"])
        lo_ci = float(s_main.loc[g, f"{metric}_mean_ci_low"])
        hi_ci = float(s_main.loc[g, f"{metric}_mean_ci_high"])
        ax.errorbar(
            m_val, base_y,
            xerr=[[m_val - lo_ci], [hi_ci - m_val]],
            fmt="o",
            color=col,
            markeredgecolor="white",
            markeredgewidth=0.7,
            capsize=2.8,
            markersize=5.8 * font_scale,
            lw=1.5,
            zorder=4,
        )
        ax.text(
            x_text, i,
            fmt_str.format(m_val),
            va="center", ha="right",
            fontsize=8.5 * font_scale,
            color=col if g in PRESET_GENRES else "#334155",
            fontweight="bold" if g in PRESET_GENRES else "normal",
            zorder=5,
        )

    ax.axvline(all_mean, color="#64748b", ls="--", lw=1.1, zorder=1)
    ax.set_yticks(y, MAIN_GENRES if show_ylabels else [""] * len(MAIN_GENRES))
    ax.set_ylim(-0.52, len(MAIN_GENRES) - 0.42)
    ax.invert_yaxis()
    ax.set_xlim(x_lo, x_hi)
    ax.set_xticks(xticks)
    ax.grid(axis="x", color="#e2e8f0", lw=0.8, zorder=0)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#94a3b8")
    ax.tick_params(axis="y", length=0)


def make_fig_q1_hue() -> None:
    """生成报告主图 figures/b/fig_q1_hue.png（并同步至 figures/fig_q1_hue.png）及两张 16:9 PPT 图。"""
    apply_plot_rc()
    raw_df = load_safe(verify_manifest=True)
    summary_df = pd.read_csv(TABLES / "genre_summary.csv")
    hue_df = pd.read_csv(TABLES / "genre_hue.csv")

    order_groups = MAIN_GENRES + ["ALL"]
    h_rows = hue_df.set_index("group").loc[order_groups].reset_index()
    s_map = summary_df.set_index("genre")
    row_labels = [
        ("全部海报" if g == "ALL" else g) + f"  (n={int(s_map.loc[g, 'n_total']):,})"
        for g in order_groups
    ]

    fig = plt.figure(figsize=(13.0, 12.8), layout="constrained")
    gs = fig.add_gridspec(3, 3, height_ratios=[1.20, 0.86, 1.12])

    ax_top = fig.add_subplot(gs[0, :])
    draw_hue_bars(ax_top, h_rows, row_labels, show_legend=True, show_summary_col=True)
    ax_top.set_title("a  九类主流电影与全库的平均色相构成（按电影等权平均）", loc="left", fontweight="bold", color="#0f172a", pad=24)

    ax_mid = fig.add_subplot(gs[1, :])
    draw_preset_sector_bars(ax_mid, hue_df, compact_ppt=False)
    ax_mid.set_title("b  主讲三类（科幻／爱情／恐怖）在 12 个 30° 色相扇区的并排占比对比", loc="left", fontweight="bold", color="#0f172a", pad=10)

    panel_tags = ["c", "d", "e"]
    for i, m in enumerate(METRICS):
        ax_m = fig.add_subplot(gs[2, i])
        draw_genre_halfeye_forest(ax_m, raw_df, summary_df, m, show_ylabels=(i == 0), font_scale=1.0)
        ax_m.set_title(f"{panel_tags[i]}  {METRIC_LABELS[m]}（分布柔影与组均值）", loc="left", fontweight="bold", color="#0f172a")
        ax_m.set_xlabel("0—1 尺度" if m != "colorful" else "Hasler–Süsstrunk 指数")

    fig.suptitle("电影类型的海报配色结构（1950—2025，N = 19,694）", fontsize=15.5, fontweight="bold", color="#0f172a")
    fig.supxlabel(
        "注：色相统计仅纳入 sat_frac ≥ 0.10 的 19,072 部有效海报；c–e 中浅色柔影与横段表示组内 10%–90% 核密度与四分位距，圆点与短横线为组均值及 95% CI，竖虚线为全库均值。",
        fontsize=9.3, color="#64748b",
    )

    FIG_B.mkdir(parents=True, exist_ok=True)
    out_b = FIG_B / "fig_q1_hue.png"
    fig.savefig(out_b, dpi=300)
    plt.close(fig)
    shutil.copy2(out_b, ROOT / "figures" / "fig_q1_hue.png")

    # PPT 16:9 图面 1：类型色相分布（16x9, dpi=150 -> 2400x1350）
    PPT_DIR.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.size": 14.5, "axes.titlesize": 16.5, "axes.labelsize": 14.5, "xtick.labelsize": 12.5, "ytick.labelsize": 13.5}):
        fig_p1 = plt.figure(figsize=(16, 9), layout="constrained")
        gs_p1 = fig_p1.add_gridspec(1, 2, width_ratios=[1.10, 1.0])
        ax1 = fig_p1.add_subplot(gs_p1[0, 0])
        draw_hue_bars(ax1, h_rows, row_labels, show_legend=True, show_summary_col=False, font_scale=1.15)
        ax1.set_title("a  九类主流电影与全库平均色相构成", loc="left", fontweight="bold", color="#0f172a", pad=38)

        ax2 = fig_p1.add_subplot(gs_p1[0, 1])
        draw_preset_sector_bars(ax2, hue_df, compact_ppt=True)
        ax2.set_title("b  科幻／爱情／恐怖 12 扇区并排对比", loc="left", fontweight="bold", color="#0f172a", pad=12)
        fig_p1.suptitle("电影类型的海报配色：色相分布\n1950—2025 · 排除近灰海报（N=19,072），按电影等权平均", fontsize=19.5, fontweight="bold", color="#0f172a")
        fig_p1.savefig(PPT_DIR / "fig_q1_genre_hue.png", dpi=150)
        plt.close(fig_p1)

    # PPT 16:9 图面 2：类型明度与色彩丰富度半眼分布图（16x9, dpi=150 -> 2400x1350）
    with plt.rc_context({"font.size": 15.5, "axes.titlesize": 17.5, "axes.labelsize": 15.5, "xtick.labelsize": 14, "ytick.labelsize": 15}):
        fig_p2, axes_p2 = plt.subplots(1, 2, figsize=(16, 9), layout="constrained")
        for idx_p, (ax_p, m) in enumerate(zip(axes_p2, ["mean_v", "colorful"])):
            draw_genre_halfeye_forest(ax_p, raw_df, summary_df, m, show_ylabels=(idx_p == 0), font_scale=1.22)
            tag = "a" if idx_p == 0 else "b"
            ax_p.set_title(f"{tag}  {METRIC_LABELS[m]}（分布柔影与组均值）", loc="left", fontweight="bold", color="#0f172a")
            ax_p.set_xlabel("组均值与影片分布（0—1 尺度）" if m == "mean_v" else "组均值与影片分布（原单位）")
        fig_p2.suptitle("电影类型的海报配色：明度与色彩丰富度\n1950—2025 · 柔影为组内影片分布，圆点与横线为组均值及 95% CI", fontsize=19.5, fontweight="bold", color="#0f172a")
        fig_p2.savefig(PPT_DIR / "fig_q1_genre_metrics.png", dpi=150)
        plt.close(fig_p2)


def make_fig_q1_comparisons() -> None:
    """生成报告对比图 figures/b/fig_q1_comparisons.png（预定对比差值 CI + 屏蔽肤色扇区稳健性对照）。"""
    apply_plot_rc()
    ct = pd.read_csv(TABLES / "genre_contrasts.csv")
    sens = pd.read_csv(TABLES / "sensitivity_checks.csv")

    fig = plt.figure(figsize=(13.0, 8.5), layout="constrained")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.28, 0.96])
    fig.suptitle("电影类型配色差异：预定对比与敏感性核验", fontsize=15.5, fontweight="bold", color="#0f172a")

    pair_keys = [("爱情", "恐怖"), ("爱情", "科幻"), ("科幻", "恐怖")]
    vs_all_genres = ["喜剧", "动画", "爱情", "科幻", "惊悚", "恐怖"]
    y_labels = [f"{a} − {b}" for a, b in pair_keys] + [f"{g} − 全库" for g in vs_all_genres]
    top_tags = ["a", "b", "c"]

    for idx, m in enumerate(METRICS):
        ax = fig.add_subplot(gs[0, idx])
        means, lo, hi, cols = [], [], [], []
        for a, b in pair_keys:
            r = ct[(ct.contrast_type == "preset_pair") & (ct.group_a == a) & (ct.group_b == b) & (ct.metric == m)].iloc[0]
            means.append(float(r.mean_difference))
            lo.append(float(r.ci_low))
            hi.append(float(r.ci_high))
            cols.append("#1e3a5f")
        for g in vs_all_genres:
            r = ct[(ct.contrast_type == "vs_all") & (ct.group_a == g) & (ct.metric == m)].iloc[0]
            means.append(float(r.mean_difference))
            lo.append(float(r.ci_low))
            hi.append(float(r.ci_high))
            cols.append("#3b6b8c")

        means_arr, lo_arr, hi_arr = np.array(means), np.array(lo), np.array(hi)
        y = np.arange(len(y_labels))

        for row_i in range(len(y)):
            if row_i % 2 == 1:
                ax.axhspan(row_i - 0.45, row_i + 0.45, facecolor="#f4f7fa", edgecolor="none", zorder=0)

        ax.axvline(0.0, color="#94a3b8", lw=1.0, zorder=1)
        ax.axhline(2.5, color="#cbd5e1", ls="--", lw=1.0, zorder=1)
        span = float(hi_arr.max() - lo_arr.min())
        ax.set_xlim(float(lo_arr.min()) - 0.12 * span, float(hi_arr.max()) + 0.34 * span)
        x_right = float(hi_arr.max()) + 0.31 * span

        for i in range(len(y)):
            ax.errorbar(
                means_arr[i], i,
                xerr=[[means_arr[i] - lo_arr[i]], [hi_arr[i] - means_arr[i]]],
                fmt="o", color=cols[i], capsize=2.8, lw=1.5, markersize=5.4, zorder=3,
            )
            fmt_d = "{:+.2f}" if m != "colorful" else "{:+.1f}"
            ax.text(x_right, i, fmt_d.format(means_arr[i]), va="center", ha="right", fontsize=8.2, color=cols[i])

        ax.set_yticks(y, y_labels if idx == 0 else [""] * len(y))
        ax.invert_yaxis()
        ax.set_title(f"{top_tags[idx]}  {METRIC_LABELS[m]}均值差", loc="left", fontweight="bold", color="#0f172a")
        ax.grid(axis="x", color="#e2e8f0", lw=0.8, zorder=0)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#94a3b8")
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel("均值差（原单位）" if m == "colorful" else "均值差（0—1 尺度）")

    # 下排左 d：全扇区色相波段占比差
    ax_b0 = fig.add_subplot(gs[1, 0])
    band_items = [
        ("爱情", "恐怖", "warm_0_60", "爱情−恐怖：0°–60° 暖色"),
        ("爱情", "科幻", "warm_0_60", "爱情−科幻：0°–60° 暖色"),
        ("科幻", "爱情", "cool_180_240", "科幻−爱情：180°–240° 青蓝"),
        ("科幻", "恐怖", "cool_180_240", "科幻−恐怖：180°–240° 青蓝"),
        ("恐怖", "爱情", "green_90_150", "恐怖−爱情：90°–150° 绿色"),
    ]
    b_means, b_lo, b_hi, b_lbls = [], [], [], []
    for ga, gb, met, lbl in band_items:
        sub_c = ct[(ct.contrast_type == "preset_pair") & (ct.metric == met)]
        hit = sub_c[(sub_c.group_a == ga) & (sub_c.group_b == gb)]
        if len(hit):
            r = hit.iloc[0]
            b_means.append(float(r.mean_difference) * 100.0)
            b_lo.append(float(r.ci_low) * 100.0)
            b_hi.append(float(r.ci_high) * 100.0)
        else:
            r = sub_c[(sub_c.group_a == gb) & (sub_c.group_b == ga)].iloc[0]
            b_means.append(-float(r.mean_difference) * 100.0)
            b_lo.append(-float(r.ci_high) * 100.0)
            b_hi.append(-float(r.ci_low) * 100.0)
        b_lbls.append(lbl)
    yb = np.arange(len(b_lbls))
    b_means_a, b_lo_a, b_hi_a = np.array(b_means), np.array(b_lo), np.array(b_hi)
    ax_b0.axvline(0.0, color="#94a3b8", lw=1.0)
    ax_b0.errorbar(
        b_means_a, yb, xerr=[b_means_a - b_lo_a, b_hi_a - b_means_a],
        fmt="o", color="#1e3a5f", capsize=3, lw=1.5, markersize=5.4,
    )
    for i_b, mv in enumerate(b_means_a):
        ax_b0.text(b_hi_a[i_b] + 0.4, i_b, f"{mv:+.1f}%", va="center", ha="left", fontsize=8.2, color="#1e3a5f")
    ax_b0.set_xlim(-1.0, 20.5)
    ax_b0.set_yticks(yb, b_lbls)
    ax_b0.invert_yaxis()
    ax_b0.set_title("d  全扇区色相波段占比差", loc="left", fontweight="bold", color="#0f172a")
    ax_b0.set_xlabel("占比差（百分点）")
    ax_b0.grid(axis="x", color="#e2e8f0", lw=0.8)
    ax_b0.spines["left"].set_visible(False)
    ax_b0.spines["bottom"].set_color("#94a3b8")
    ax_b0.tick_params(axis="y", length=0)

    # 下排中 e：屏蔽 0°-60° 红橙黄肤色区后重归一（带 95% CI 误差须）
    ax_b1 = fig.add_subplot(gs[1, 1])
    sg = sens[sens.check_family == "skin_sector_group_level"]
    x_pos = np.arange(len(PRESET_GENRES))
    w_bar = 0.34
    c_vals, c_lo, c_hi, g_vals, g_lo, g_hi = [], [], [], [], [], []
    for g in PRESET_GENRES:
        rc = sg[(sg.setting == g) & (sg.metric == "cool_180_240_noskin")].iloc[0]
        rg = sg[(sg.setting == g) & (sg.metric == "green_90_150_noskin")].iloc[0]
        c_vals.append(float(rc.estimate) * 100.0); c_lo.append(float(rc.ci_low) * 100.0); c_hi.append(float(rc.ci_high) * 100.0)
        g_vals.append(float(rg.estimate) * 100.0); g_lo.append(float(rg.ci_low) * 100.0); g_hi.append(float(rg.ci_high) * 100.0)

    c_arr, g_arr = np.array(c_vals), np.array(g_vals)
    ax_b1.bar(
        x_pos - w_bar / 2, c_arr, width=w_bar, color="#1d6fa5", alpha=0.90,
        yerr=[c_arr - np.array(c_lo), np.array(c_hi) - c_arr], capsize=2.5, error_kw=dict(lw=1.0, ecolor="#0f172a"),
        label="180°–240° 青蓝",
    )
    ax_b1.bar(
        x_pos + w_bar / 2, g_arr, width=w_bar, color="#2f855a", alpha=0.90,
        yerr=[g_arr - np.array(g_lo), np.array(g_hi) - g_arr], capsize=2.5, error_kw=dict(lw=1.0, ecolor="#0f172a"),
        label="90°–150° 黄绿／绿",
    )
    for idx_g in range(len(PRESET_GENRES)):
        ax_b1.text(idx_g - w_bar / 2, c_hi[idx_g] + 1.0, f"{c_vals[idx_g]:.1f}%", ha="center", fontsize=8.3, fontweight="bold", color="#1d6fa5")
        ax_b1.text(idx_g + w_bar / 2, g_hi[idx_g] + 1.0, f"{g_vals[idx_g]:.1f}%", ha="center", fontsize=8.3, fontweight="bold", color="#2f855a")
    ax_b1.set_xticks(x_pos, PRESET_GENRES)
    ax_b1.set_ylim(0, 58)
    ax_b1.set_ylabel("非肤色扇区内占比（%）")
    ax_b1.set_title("e  屏蔽 0°–60° 肤色区后重归一", loc="left", fontweight="bold", color="#0f172a")
    ax_b1.legend(loc="upper right", frameon=False, fontsize=8.3)
    ax_b1.grid(axis="y", color="#e2e8f0", lw=0.8)
    ax_b1.spines["bottom"].set_color("#94a3b8")
    ax_b1.spines["left"].set_color("#94a3b8")

    # 下排右 f：sat_frac 阈值扫描
    ax_b2 = fig.add_subplot(gs[1, 2])
    st = sens[sens.check_family == "sat_frac_threshold_scan"]
    ths = [0.05, 0.10, 0.15, 0.20]
    series_cfg = [
        ("科幻_minus_爱情", "cool_180_240", "科幻−爱情（青蓝）", "#1d6fa5"),
        ("爱情_minus_恐怖", "warm_0_60", "爱情−恐怖（暖色）", "#d95f2b"),
        ("恐怖_minus_爱情", "green_90_150", "恐怖−爱情（绿色）", "#2f855a"),
    ]
    for suffix, met, lbl, col in series_cfg:
        ys_est, ys_lo, ys_hi = [], [], []
        for th in ths:
            r = st[(st.setting == f"sat_frac>={th:.2f}_{suffix}") & (st.metric == met)].iloc[0]
            ys_est.append(float(r.estimate) * 100.0)
            ys_lo.append(float(r.ci_low) * 100.0)
            ys_hi.append(float(r.ci_high) * 100.0)
        ax_b2.plot(ths, ys_est, "o-", color=col, lw=1.9, markersize=5, label=lbl)
        ax_b2.fill_between(ths, ys_lo, ys_hi, color=col, alpha=0.14)
    ax_b2.axvline(0.10, color="#64748b", ls="--", lw=1.0)
    ax_b2.set_xticks(ths, ["0.05", "0.10\n(主口径)", "0.15", "0.20"])
    ax_b2.set_xlabel("近灰过滤阈值 sat_frac 下限")
    ax_b2.set_ylabel("占比差（百分点）")
    ax_b2.set_title("f  sat_frac 阈值敏感性扫描", loc="left", fontweight="bold", color="#0f172a")
    ax_b2.legend(loc="center right", frameon=False, fontsize=8.2)
    ax_b2.grid(color="#e2e8f0", lw=0.8)
    ax_b2.spines["bottom"].set_color("#94a3b8")
    ax_b2.spines["left"].set_color("#94a3b8")

    fig.supxlabel(
        "注：所有差值区间均由整库电影级联合重采样 Bootstrap（1,000 次）估计逐项 95% CI，同步保留多标签重叠影片协方差。",
        fontsize=9.3, color="#64748b",
    )
    fig.savefig(FIG_B / "fig_q1_comparisons.png", dpi=300)
    plt.close(fig)


def draw_pca_scatter(ax: plt.Axes, assign_df: pd.DataFrame, full_df: pd.DataFrame, cluster_sum: pd.DataFrame, font_scale: float = 1.0) -> None:
    """绘制四类客观色型在 PCA 二维空间的核密度轮廓域 + 三主色融合真实色彩云 + 双环质心标。"""
    merged = assign_df.merge(
        full_df[["id", "dom1", "dom2", "dom3", "ds1", "ds2", "ds3", "mean_v", "mean_s", "hue"]],
        on="id", how="left",
    )

    # 背景：各簇柔和核密度等高线边界
    gx, gy = np.meshgrid(np.linspace(-3.2, 4.2, 90), np.linspace(-3.6, 2.8, 90))
    grid_pts = np.vstack([gx.ravel(), gy.ravel()])
    contour_cols = {0: "#94a3b8", 1: "#d95f2b", 2: "#1d6fa5", 3: "#334155"}
    for cid in CLUSTER_IDS:
        sub_c = merged[merged["cluster"] == cid]
        kde_c = gaussian_kde(np.vstack([sub_c["pc1"].to_numpy(), sub_c["pc2"].to_numpy()]), bw_method=0.35)
        zz = kde_c(grid_pts).reshape(gx.shape)
        thr = np.percentile(zz, [82, 93])
        ax.contour(gx, gy, zz, levels=thr, colors=[contour_cols[cid]], linewidths=0.85, alpha=0.35, zorder=1)

    rng = np.random.default_rng(SEED)
    smp = merged.iloc[rng.choice(len(merged), size=min(4000, len(merged)), replace=False)]
    pt_colors = blended_poster_colors(smp)

    ax.scatter(smp["pc1"], smp["pc2"], c=pt_colors, s=11.5 * font_scale, alpha=0.62, linewidths=0, zorder=2)

    for _, row in cluster_sum.iterrows():
        cid = int(row["cluster"])
        cx, cy = float(row["pc1_mean"]), float(row["pc2_mean"])
        cname = str(row["cluster_name"])
        share_pct = float(row["share"]) * 100.0
        ax.scatter([cx], [cy], s=230 * (font_scale ** 1.25), facecolor="white", edgecolor="#0f172a", lw=1.2, alpha=0.92, zorder=5)
        ax.scatter([cx], [cy], s=115 * (font_scale ** 1.25), facecolor=ARCHETYPE_COLORS[cid], edgecolor="#0f172a", lw=1.1, zorder=6)

        dy = 0.40 if cid in (0, 3) else (-0.44 if cid == 2 else 0.40)
        ax.text(
            cx, cy + dy,
            f"{cname}（{share_pct:.1f}%）",
            ha="center", va="center",
            fontsize=9.4 * font_scale,
            fontweight="bold",
            color="#0f172a",
            bbox=dict(boxstyle="round,pad=0.20", fc="white", ec="#cbd5e1", lw=0.6, alpha=0.90),
            zorder=7,
        )

    ax.axhline(0, color="#cbd5e1", lw=0.8, ls="--", zorder=0)
    ax.axvline(0, color="#cbd5e1", lw=0.8, ls="--", zorder=0)
    ax.set_xlim(-3.2, 4.2)
    ax.set_ylim(-3.6, 2.8)
    ax.set_xlabel("第一主成分 PC1（37.7%：饱和度与暖色丰富度轴）")
    ax.set_ylabel("第二主成分 PC2（26.6%：明亮浅调 vs 青蓝冷调轴）")
    ax.grid(color="#eef2f6", lw=0.8, zorder=0)
    ax.spines["bottom"].set_color("#94a3b8")
    ax.spines["left"].set_color("#94a3b8")


def draw_cluster_by_genre_bars(ax: plt.Axes, by_genre_df: pd.DataFrame, font_scale: float = 1.0) -> None:
    """绘制 9 大类型与全库基线在四类客观色型上的 100% 堆叠水平条。"""
    order = MAIN_GENRES + ["ALL"]
    sub = by_genre_df.set_index("genre").loc[order].reset_index()
    y = np.arange(len(sub))
    left = np.zeros(len(sub), dtype=float)

    for cid in CLUSTER_IDS:
        vals = sub[f"share_c{cid}"].to_numpy(dtype=float) * 100.0
        ax.barh(
            y, vals, left=left, height=0.68,
            color=ARCHETYPE_COLORS[cid],
            edgecolor="white", lw=0.9,
            label=CLUSTER_NAMES[cid],
        )
        txt_col = "#0f172a" if cid == 0 else "white"
        for row_i, v in enumerate(vals):
            if v >= 15.5:
                ax.text(
                    left[row_i] + v / 2.0, row_i,
                    f"{v:.0f}%",
                    ha="center", va="center",
                    fontsize=8.4 * font_scale,
                    color=txt_col,
                    fontweight="bold" if v >= 30.0 else "normal",
                )
        left += vals

    labels = [("全部海报" if r.genre == "ALL" else r.genre) + f"  (n={int(r.n_hue):,})" for r in sub.itertuples()]
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("色型构成占比（%）")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#94a3b8")
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.00), ncol=4, frameon=False, fontsize=9.0 * font_scale)


def make_fig_q1_cluster() -> None:
    """生成报告聚类图 figures/b/fig_q1_cluster.png 与 16:9 PPT 图 outputs/b/ppt/fig_q1_cluster.png。"""
    apply_plot_rc()
    x = load_safe(verify_manifest=True)
    bench = pd.read_csv(TABLES / "cluster_benchmark.csv")
    assign_df = pd.read_csv(TABLES / "cluster_assignments.csv")
    cluster_sum = pd.read_csv(TABLES / "cluster_summary.csv")
    by_genre = pd.read_csv(TABLES / "cluster_by_genre.csv")

    fig = plt.figure(figsize=(13.4, 11.0), layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.12], width_ratios=[1.0, 1.12])
    fig.suptitle("无监督海报色型聚类：选型依据、二维色度流形与电影类型构成", fontsize=15.5, fontweight="bold", color="#0f172a")

    # 面板 a（左上）：双指标选型（DB 指数 ↓ 与子样本稳定性 ARI ↑）
    ax_tl = fig.add_subplot(gs[0, 0])
    km_conic = bench[(bench.feature_space == "Conic_5D") & (bench.model == "K-Means")].sort_values("k")
    km_base = bench[(bench.feature_space == "Base_5D") & (bench.model == "K-Means")].sort_values("k")

    l1, = ax_tl.plot(km_conic["k"], km_conic["davies_bouldin"], "o-", color="#1d6fa5", lw=2.1, markersize=6, label="Conic_5D：DB 指数（左轴 ↓）")
    l2, = ax_tl.plot(km_base["k"], km_base["davies_bouldin"], "s--", color="#94a3b8", lw=1.4, markersize=4.8, label="Base_5D：DB 指数（对照 ↓）")

    ax_tl_r = ax_tl.twinx()
    ax_tl_r.spines["top"].set_visible(False)
    ax_tl_r.spines["right"].set_visible(True)
    ax_tl_r.spines["right"].set_color("#d95f2b")
    l3, = ax_tl_r.plot(km_conic["k"], km_conic["stability_ari"], "^-.", color="#d95f2b", lw=1.7, markersize=5.5, label="Conic_5D：子样本稳定性 ARI（右轴 ↑）")
    ax_tl_r.set_ylim(0.955, 1.002)
    ax_tl_r.set_yticks([0.96, 0.98, 1.00])
    ax_tl_r.set_ylabel("子样本重训一致性 ARI", color="#d95f2b")
    ax_tl_r.tick_params(axis="y", colors="#d95f2b")

    row_k4 = km_conic[km_conic["k"] == 4].iloc[0]
    ax_tl.axvline(4, color="#cbd5e1", ls=":", lw=1.1, zorder=0)
    ax_tl.scatter([4], [row_k4["davies_bouldin"]], s=130, facecolor="none", edgecolor="#b91c1c", lw=2.0, zorder=5)
    ax_tl.text(
        4.0, float(row_k4["davies_bouldin"]) - 0.042,
        f"k = 4 最优（DB = {row_k4['davies_bouldin']:.3f}，ARI = {row_k4['stability_ari']:.3f}）",
        ha="center", va="top", fontsize=8.6, color="#991b1b", fontweight="bold",
    )
    ax_tl.set_xticks([2, 3, 4, 5, 6])
    ax_tl.set_ylim(1.08, 1.62)
    ax_tl.set_xlabel("聚类簇数 k")
    ax_tl.set_ylabel("Davies–Bouldin 指数（越小分离越优）", color="#1d6fa5")
    ax_tl.set_title("a  K-Means 簇数选型与稳定性验证（N = 19,072）", loc="left", fontweight="bold", color="#0f172a")
    ax_tl.legend(handles=[l1, l2, l3], loc="upper right", frameon=False, fontsize=8.0)
    ax_tl.grid(color="#e2e8f0", lw=0.8)
    ax_tl.spines["bottom"].set_color("#94a3b8")
    ax_tl.spines["left"].set_color("#1d6fa5")

    # 面板 b（右上）：PCA 二维主成分空间
    ax_tr = fig.add_subplot(gs[0, 1])
    draw_pca_scatter(ax_tr, assign_df, x, cluster_sum, font_scale=1.0)
    ax_tr.set_title("b  二维主成分空间的四类色型（n = 4,000 三主色融合）", loc="left", fontweight="bold", color="#0f172a")

    # 面板 c（左下）：四类客观色型的平均色相构成与三指标均值
    ax_bl = fig.add_subplot(gs[1, 0])
    c_hue_rows = cluster_sum.assign(n_hue=cluster_sum["n_total"])
    c_labels = [
        f"{r.cluster_name}  ({r.share*100:.1f}%)\nV={r.mean_v_mean:.2f} · S={r.mean_s_mean:.2f} · C={r.colorful_mean:.0f}"
        for r in cluster_sum.itertuples()
    ]
    draw_hue_bars(ax_bl, c_hue_rows, c_labels, show_legend=True, show_summary_col=False)
    ax_bl.set_title("c  四类客观色型的色相构成与核心指标均值", loc="left", fontweight="bold", color="#0f172a", pad=28)

    # 面板 d（右下）：9 大类型在四类色型上的构成占比
    ax_br = fig.add_subplot(gs[1, 1])
    draw_cluster_by_genre_bars(ax_br, by_genre, font_scale=1.0)
    ax_br.set_title("d  各电影类型的客观色型构成占比", loc="left", fontweight="bold", color="#0f172a", pad=28)

    fig.supxlabel(
        "注：聚类在 sat_frac ≥ 0.10 的 19,072 部海报上基于标准化圆锥色度特征 [V, S, colorful, S·cosH, S·sinH] 完成，全程不使用任何类型标签。",
        fontsize=9.3, color="#64748b",
    )
    fig.savefig(FIG_B / "fig_q1_cluster.png", dpi=300)
    plt.close(fig)

    # PPT 16:9 图面 3：无监督色型聚类与类型构成（16x9, dpi=150 -> 2400x1350）
    with plt.rc_context({"font.size": 14.5, "axes.titlesize": 16.5, "axes.labelsize": 14.5, "xtick.labelsize": 13, "ytick.labelsize": 13.5}):
        fig_p3 = plt.figure(figsize=(16, 9), layout="constrained")
        gs_p3 = fig_p3.add_gridspec(1, 2, width_ratios=[1.02, 1.08])
        ax_p_left = fig_p3.add_subplot(gs_p3[0, 0])
        draw_pca_scatter(ax_p_left, assign_df, x, cluster_sum, font_scale=1.20)
        ax_p_left.set_title("a  二维主成分空间的四类色型（方差解释 64.3%）", loc="left", fontweight="bold", color="#0f172a")

        ax_p_right = fig_p3.add_subplot(gs_p3[0, 1])
        draw_cluster_by_genre_bars(ax_p_right, by_genre, font_scale=1.20)
        ax_p_right.set_title("b  九类主流电影与全库的色型构成", loc="left", fontweight="bold", color="#0f172a", pad=38)

        fig_p3.suptitle("不预设类型的无监督聚类：四类客观色型与类型分布\n1950—2025 · N=19,072 部（sat_frac ≥ 0.10）", fontsize=19.5, fontweight="bold", color="#0f172a")
        fig_p3.savefig(PPT_DIR / "fig_q1_cluster.png", dpi=150)
        plt.close(fig_p3)


def main() -> None:
    make_fig_q1_hue()
    make_fig_q1_comparisons()
    make_fig_q1_cluster()
    print("B 组升级版出版级报告图（300 DPI）与 16:9 PPT 图面（150 DPI）全部绘制完成。")


if __name__ == "__main__":
    main()
