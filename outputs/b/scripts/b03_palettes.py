"""按可复现距离准则为四类色型与代表电影类型各选一张中心海报，生成 14×10 保真几何色块与底部比例色卡图。"""
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter, label
from sklearn.cluster import KMeans

from b_common import (
    CLUSTER_IDS,
    CLUSTER_NAMES,
    FIG_B,
    HUE_COLS,
    MAIN_GENRES,
    METRICS,
    OUT,
    PALETTE_GENRES_8,
    PPT_DIR,
    PPT_PALETTE_GENRES_4,
    ROOT,
    SAT_FRAC_MIN,
    SEED,
    TABLES,
    apply_plot_rc,
    common,
    eligible_hue_mask,
    load_safe,
)


def select_example(group: pd.DataFrame, dimension: str, key: str, used_ids: set[int] | None = None) -> dict:
    """选择最接近组内三指标中位数与平均色相构成的真实海报（非动画类型排除动画合集标签以避免跨介质混杂）。"""
    work = group
    if dimension == "genre" and key != "动画":
        non_anim = group[~common.has_genre(group, "动画")]
        if len(non_anim) >= 30:
            work = non_anim

    good = eligible_hue_mask(work, sat_min=SAT_FRAC_MIN)
    sample = work.loc[good].copy()
    if len(sample) < 30:
        raise ValueError(f"{dimension}/{key}: 可用样本不足 30")

    features = sample[METRICS].to_numpy(dtype=float)
    hues = sample[HUE_COLS].to_numpy(dtype=float)
    hues = hues / hues.sum(axis=1, keepdims=True)

    med = np.median(features, axis=0)
    iqr = np.percentile(features, 75, axis=0) - np.percentile(features, 25, axis=0)
    iqr[iqr == 0] = 1.0

    metric_dist = np.mean(((features - med) / iqr) ** 2, axis=1)
    hue_dist = np.abs(hues - hues.mean(axis=0)).sum(axis=1) / 2.0

    sample["selection_score"] = metric_dist + hue_dist ** 2
    sample["metric_distance"] = metric_dist
    sample["hue_distance"] = hue_dist
    ranked = sample.sort_values(["selection_score", "id"])

    selected = None
    for _, r in ranked.iterrows():
        pid = int(r.id)
        if used_ids is not None and pid in used_ids:
            continue
        if (ROOT / "data" / "posters" / f"{pid}.jpg").is_file():
            selected = r
            break
    if selected is None:
        raise ValueError(f"{dimension}/{key}: 未找到可用海报图片")

    poster_path = ROOT / "data" / "posters" / f"{int(selected.id)}.jpg"
    return {
        "dimension": dimension,
        "group": str(key),
        "n_total": int(len(group)),
        "n_candidates": int(len(sample)),
        "id": int(selected.id),
        "title": str(selected.title),
        "year": int(selected.year),
        "selection_score": float(selected.selection_score),
        "metric_distance": float(selected.metric_distance),
        "hue_distance": float(selected.hue_distance),
        "poster_sha256": hashlib.sha256(poster_path.read_bytes()).hexdigest(),
    }


def abstract_poster(movie_id: int) -> tuple[np.ndarray, list[str], np.ndarray]:
    """保真几何色块抽象：先轻度去噪并用 K-Means(k=7) 提炼真实主色（避免大核 RGB 模糊把互补色混成灰褐色），
    再在类别指示掩膜上平滑并归纳为 14×10 连续色块网格，按面积降序排列主色。
    """
    poster_path = ROOT / "data" / "posters" / f"{movie_id}.jpg"
    with Image.open(poster_path) as src:
        src = src.convert("RGB")
        src = src.crop((0, 0, src.width, int(src.height * 0.88)))
        src = src.resize((120, 168), Image.Resampling.BOX)
        arr = gaussian_filter(np.asarray(src, dtype=float), sigma=(1.0, 1.0, 0.0))
        flat = arr.reshape(-1, 3)

        km = KMeans(n_clusters=7, random_state=SEED, n_init=10).fit(flat)
        centers = np.clip(np.round(km.cluster_centers_), 0, 255).astype(np.uint8)
        labels = km.labels_.reshape(168, 120)

        support = np.stack(
            [gaussian_filter((labels == i).astype(float), sigma=2.6) for i in range(7)],
            axis=-1,
        )
        # 168 = 14 * 12, 120 = 10 * 12 -> 14x10 方形网格
        grid = support.reshape(14, 12, 10, 12, 7).mean(axis=(1, 3)).argmax(axis=-1)

        for _ in range(3):
            changed = False
            for col_idx in range(7):
                comps, cnt = label(grid == col_idx)
                for comp_id in range(1, cnt + 1):
                    reg = comps == comp_id
                    if reg.sum() >= 2:
                        continue
                    neigh = grid[binary_dilation(reg) & (~reg)]
                    if len(neigh):
                        grid[reg] = np.bincount(neigh, minlength=7).argmax()
                        changed = True
            if not changed:
                break

        raw_shares = np.bincount(grid.ravel(), minlength=7) / grid.size
        order = np.argsort(-raw_shares)
        remap = np.empty(7, dtype=int)
        remap[order] = np.arange(7)
        grid_sorted = remap[grid]
        centers_sorted = centers[order]
        shares_sorted = raw_shares[order]

        hex_colors = ["#%02x%02x%02x" % tuple(c) for c in centers_sorted]
        mosaic_rgb = centers_sorted[grid_sorted]
        return mosaic_rgb, hex_colors, shares_sorted


def render_card_on_axis(ax: plt.Axes, mosaic_rgb: np.ndarray, hex_colors: list[str], shares: np.ndarray) -> None:
    """在单个子图内绘制上方 14×10 几何海报色块与下方等宽比例色卡条。"""
    # 构造高分辨率无插值画布：海报区 280×200px + 白缝 10px + 底部比例色卡 22px = 312×200px
    cell = 20
    h_img, w_img = 14 * cell, 10 * cell
    gap = 10
    bar_h = 22
    canvas = np.full((h_img + gap + bar_h, w_img, 3), 255, dtype=np.uint8)

    poster_up = np.repeat(np.repeat(mosaic_rgb, cell, axis=0), cell, axis=1)
    # 给海报区外圈加 1px 柔和浅边线，防止纯白海报与页面融为一体
    poster_up[0, :] = [203, 213, 225]
    poster_up[-1, :] = [203, 213, 225]
    poster_up[:, 0] = [203, 213, 225]
    poster_up[:, -1] = [203, 213, 225]
    canvas[:h_img, :, :] = poster_up

    # 绘制底部比例色卡条
    x_cur = 0
    nonzero = [(hx, sh) for hx, sh in zip(hex_colors, shares) if sh > 0]
    for idx_c, (hx, sh) in enumerate(nonzero):
        rgb = [int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)]
        x_next = w_img if idx_c == len(nonzero) - 1 else min(w_img, int(round(x_cur + sh * w_img)))
        if x_next > x_cur:
            canvas[h_img + gap :, x_cur:x_next, :] = rgb
            if x_cur > 0:
                canvas[h_img + gap :, x_cur : min(w_img, x_cur + 2), :] = 255
        x_cur = x_next

    canvas[h_img + gap, :, :] = [203, 213, 225]
    canvas[-1, :, :] = [203, 213, 225]
    canvas[h_img + gap :, 0, :] = [203, 213, 225]
    canvas[h_img + gap :, -1, :] = [203, 213, 225]

    ax.imshow(canvas, interpolation="nearest", aspect="equal")
    ax.axis("off")


def draw_report_palettes(cluster_rows: list[dict], genre_map: dict[str, dict], cache: dict[int, tuple]) -> None:
    apply_plot_rc()
    fig = plt.figure(figsize=(13, 14.8))
    gs = fig.add_gridspec(3, 4, left=0.04, right=0.96, bottom=0.055, top=0.895, wspace=0.14, hspace=0.22)

    fig.text(0.04, 0.958, "四类无监督色型与代表电影类型的中心海报抽象配色卡", fontsize=16, fontweight="bold", color="#0f172a")
    fig.text(
        0.04, 0.932,
        "上排为圆锥色度聚类所得四类客观色型的中心示例，中下两排为八类主流电影的组中心示例；每卡下方附该海报 7 主色面积比例条",
        fontsize=10.2, color="#475569",
    )

    for col_i, r in enumerate(cluster_rows):
        ax = fig.add_subplot(gs[0, col_i])
        ax.set_title(f"色型 · {r['group']}", fontsize=12, loc="left", fontweight="bold", color="#0f172a", pad=7)
        mosaic_rgb, hx, sh = cache[r["id"]]
        render_card_on_axis(ax, mosaic_rgb, hx, sh)

    for idx, g in enumerate(PALETTE_GENRES_8):
        r = genre_map[g]
        ax = fig.add_subplot(gs[1 + idx // 4, idx % 4])
        ax.set_title(f"类型 · {g}", fontsize=12, loc="left", fontweight="bold", color="#334155", pad=7)
        mosaic_rgb, hx, sh = cache[r["id"]]
        render_card_on_axis(ax, mosaic_rgb, hx, sh)

    fig.text(
        0.04, 0.018,
        "注：每幅卡片由距该组指标中位数与平均色相分布最近的一张原语言海报经 K-Means(k=7) 量化与 14×10 空间平滑生成，仅作视觉直观对照，不代表整组分布。",
        fontsize=9.5, color="#64748b",
    )
    FIG_B.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_B / "fig_q1_palettes.png", dpi=300)
    plt.close(fig)


def draw_ppt_palettes(cluster_rows: list[dict], genre_map: dict[str, dict], cache: dict[int, tuple]) -> None:
    apply_plot_rc()
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(2, 4, left=0.04, right=0.96, bottom=0.08, top=0.83, wspace=0.14, hspace=0.22)
    fig.text(0.04, 0.93, "四类客观色型与典型类型的海报抽象配色卡", fontsize=21, fontweight="bold", color="#0f172a")
    fig.text(0.04, 0.882, "上排：无监督四类色型中心海报 · 下排：四类代表电影类型中心海报（底部横条为单片主色占比）", fontsize=13.5, color="#475569")

    for col_i, r in enumerate(cluster_rows):
        ax = fig.add_subplot(gs[0, col_i])
        ax.set_title(f"色型 · {r['group']}", fontsize=15.5, loc="left", fontweight="bold", color="#0f172a", pad=6)
        mosaic_rgb, hx, sh = cache[r["id"]]
        render_card_on_axis(ax, mosaic_rgb, hx, sh)

    for col_i, g in enumerate(PPT_PALETTE_GENRES_4):
        r = genre_map[g]
        ax = fig.add_subplot(gs[1, col_i])
        ax.set_title(f"类型 · {g}", fontsize=15.5, loc="left", fontweight="bold", color="#334155", pad=6)
        mosaic_rgb, hx, sh = cache[r["id"]]
        render_card_on_axis(ax, mosaic_rgb, hx, sh)

    fig.text(
        0.04, 0.024,
        "每幅图简化自距组中心最近的单张真实海报（14×10 连续色块 + 主色比例条），用于直观感受配色，不能替代整组统计。",
        fontsize=12.5, color="#64748b",
    )
    PPT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PPT_DIR / "fig_q1_palettes.png", dpi=150)
    plt.close(fig)


def main() -> None:
    x = load_safe(verify_manifest=True)
    cl_df = pd.read_csv(TABLES / "cluster_assignments.csv")
    u = x.merge(cl_df[["id", "cluster", "cluster_name"]], on="id", how="inner", validate="one_to_one")

    used: set[int] = set()
    cluster_examples = []
    for cid in CLUSTER_IDS:
        cname = CLUSTER_NAMES[cid]
        ex = select_example(u[u["cluster"] == cid], "cluster", cname, used_ids=used)
        used.add(ex["id"])
        cluster_examples.append(ex)

    genre_examples = []
    for g in MAIN_GENRES:
        ex = select_example(x[common.has_genre(x, g)], "genre", g, used_ids=used)
        used.add(ex["id"])
        genre_examples.append(ex)

    all_examples = cluster_examples + genre_examples
    cache: dict[int, tuple] = {}
    for row in all_examples:
        mosaic_rgb, colors, shares = abstract_poster(row["id"])
        cache[row["id"]] = (mosaic_rgb, colors, shares)
        for i, (c_hex, sh) in enumerate(zip(colors, shares), 1):
            row[f"color{i}"] = c_hex
            row[f"share{i}"] = float(sh)

    pd.DataFrame(all_examples).to_csv(TABLES / "palette_examples.csv", index=False, encoding="utf-8")

    manifest = {
        "selection": "mean squared IQR-scaled distance to group metric medians + squared hue TVD to group mean (non-animation genres exclude multi-tagged animation films); ties by id",
        "selection_hue_min_sat_frac": SAT_FRAC_MIN,
        "crop_bottom_fraction": 0.12,
        "quantizer": "KMeans(n_clusters=7, seed=42, n_init=10) after sigma=1.0 anti-aliasing",
        "region_smoothing_sigma": 2.6,
        "grid_columns": 10,
        "grid_rows": 14,
        "minimum_component_cells": 2,
        "swatch_bar": "proportional 7-color horizontal barcode beneath each 14x10 mosaic",
        "posters_sha256": {str(r["id"]): r["poster_sha256"] for r in all_examples},
        "input_manifest": "run_manifest.json",
    }
    (OUT / "palette_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    genre_map = {r["group"]: r for r in genre_examples}
    draw_report_palettes(cluster_examples, genre_map, cache)
    draw_ppt_palettes(cluster_examples, genre_map, cache)
    print(f"升级版典型海报配色卡完成：4 类色型 + {len(genre_examples)} 类电影类型。")


if __name__ == "__main__":
    main()
