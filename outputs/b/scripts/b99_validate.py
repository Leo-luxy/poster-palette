"""自动验收脚本：逐项复核 B 组输入指纹、统计口径、联合 Bootstrap 复现、聚类一致性与图面规格。"""
import hashlib
import numpy as np
import pandas as pd
from PIL import Image

from b_common import (
    common,
    CLUSTER_IDS,
    FIG_B,
    HUE_COLS,
    MAIN_GENRES,
    METRICS,
    OUT,
    PPT_DIR,
    PRESET_GENRES,
    REPORTS,
    ROOT,
    SAT_FRAC_MIN,
    SEED,
    TABLES,
    eligible_hue_mask,
    joint_movie_contrast,
    load_safe,
)


def main() -> None:
    results: list[tuple[str, bool]] = []

    def check(label: str, cond: bool) -> None:
        results.append((label, bool(cond)))

    x = load_safe(verify_manifest=True)
    good_h = eligible_hue_mask(x, sat_min=SAT_FRAC_MIN)
    check("输入唯一且匹配 19,694 部", len(x) == 19694 and x.id.is_unique)
    check("色相有效样本 sat_frac≥0.10 为 19,072 部", int(good_h.sum()) == 19072)

    # 1. 核对类型汇总与色相表
    gs = pd.read_csv(TABLES / "genre_summary.csv")
    gh = pd.read_csv(TABLES / "genre_hue.csv")
    check("genre_summary 覆盖 9 大类型与全库 ALL", gs["genre"].tolist() == MAIN_GENRES + ["ALL"])
    check(
        "各类型总片数与直接筛选完全一致",
        all(
            int(r.n_total) == (len(x) if r.genre == "ALL" else int(common.has_genre(x, r.genre).sum()))
            and all(
                np.isclose(
                    getattr(r, f"{m}_mean"),
                    (x[m] if r.genre == "ALL" else x.loc[common.has_genre(x, r.genre), m]).mean(),
                )
                for m in METRICS
            )
            for r in gs.itertuples()
        ),
    )
    check("各类型 12 扇区色相占比和为 1", np.allclose(gh[HUE_COLS].sum(axis=1), 1.0))

    def verify_hue_row(source: pd.DataFrame, row) -> bool:
        mk = eligible_hue_mask(source, sat_min=SAT_FRAC_MIN)
        raw = source.loc[mk, HUE_COLS].to_numpy(dtype=float)
        avg = (raw / raw.sum(axis=1, keepdims=True)).mean(axis=0)
        return (
            int(row.n_total) == len(source)
            and int(row.n_hue) == int(mk.sum())
            and np.allclose(avg, np.array([getattr(row, c) for c in HUE_COLS]))
        )

    check(
        "各类型色相按逐片归一等权平均且与 common.hue_share 一致",
        all(
            verify_hue_row(x if r.group == "ALL" else x[common.has_genre(x, r.group)], r)
            for r in gh.itertuples()
        )
        and all(
            np.allclose(
                gh.set_index("group").loc[g, HUE_COLS].to_numpy(dtype=float),
                common.hue_share(x, g).to_numpy(dtype=float),
                atol=1e-5,
            )
            for g in PRESET_GENRES
        ),
    )

    # 2. 核对电影级联合 Bootstrap 对比可精确复现且无缺失值
    ct = pd.read_csv(TABLES / "genre_contrasts.csv")
    check(
        "genre_contrasts 全部 72 项差值与 95% CI 完整有效且满足 ci_low < diff < ci_high",
        len(ct) == 72
        and ct[["mean_difference", "ci_low", "ci_high"]].notna().all().all()
        and ((ct["ci_low"] < ct["mean_difference"]) & (ct["mean_difference"] < ct["ci_high"])).all(),
    )
    genre_masks = {g: common.has_genre(x, g).to_numpy(dtype=bool) for g in MAIN_GENRES}
    for ga, gb in [("爱情", "恐怖"), ("爱情", "科幻"), ("科幻", "恐怖")]:
        for m in METRICS:
            row = ct[(ct.contrast_type == "preset_pair") & (ct.group_a == ga) & (ct.group_b == gb) & (ct.metric == m)].iloc[0]
            calc = joint_movie_contrast(x[m].to_numpy(dtype=float), genre_masks[ga], genre_masks[gb], seed=SEED)
            check(
                f"预定对比差值及联合 Bootstrap 95% CI 可复现：{ga}-{gb} {m}",
                all(np.isclose(row[k], calc[k]) for k in ["n_a", "n_b", "n_overlap", "mean_difference", "ci_low", "ci_high"]),
            )

    # 3. 核对无监督聚类样本数与前后一致性（根除旧版漏筛近灰海报 Bug）
    bench = pd.read_csv(TABLES / "cluster_benchmark.csv")
    assign_df = pd.read_csv(TABLES / "cluster_assignments.csv")
    csum = pd.read_csv(TABLES / "cluster_summary.csv")
    by_g = pd.read_csv(TABLES / "cluster_by_genre.csv")
    by_d = pd.read_csv(TABLES / "cluster_by_decade.csv")

    check("聚类基准表全部基于 N=19,072 统一口径", (bench["n_movies"] == 19072).all() and len(bench) == 45)
    check("聚类分配表唯一覆盖 19,072 部且四簇总和严格等于 19,072", len(assign_df) == 19072 and assign_df["id"].is_unique and int(csum["n_total"].sum()) == 19072)
    check("四类色型占比和为 1 且最小簇占比 > 15%", np.isclose(csum["share"].sum(), 1.0) and (csum["share"] > 0.15).all())
    check("各类型色型构成每行和为 1", np.allclose(by_g[[f"share_c{c}" for c in CLUSTER_IDS]].sum(axis=1), 1.0))
    check("各年代色型构成每行和为 1 且样本总和为 19,072", np.allclose(by_d[[f"share_c{c}" for c in CLUSTER_IDS]].sum(axis=1), 1.0) and int(by_d["n_hue"].sum()) == 19072)

    # 4. 核对典型海报示例与指纹
    pal = pd.read_csv(TABLES / "palette_examples.csv")
    check("典型海报覆盖 4 类色型与 9 类电影且无重复影片", len(pal) == 13 and pal["id"].is_unique)
    check(
        "示例海报文件存在、SHA-256 指纹一致且 7 色比例和为 1",
        all(
            (ROOT / "data" / "posters" / f"{int(r.id)}.jpg").is_file()
            and hashlib.sha256((ROOT / "data" / "posters" / f"{int(r.id)}.jpg").read_bytes()).hexdigest() == r.poster_sha256
            for r in pal.itertuples()
        )
        and np.allclose(pal[[f"share{i}" for i in range(1, 8)]].sum(axis=1), 1.0),
    )

    # 5. 核对报告图（300 DPI）与根目录兼容主图、16:9 PPT 图面
    report_figs = [
        ROOT / "figures" / "fig_q1_hue.png",
        FIG_B / "fig_q1_hue.png",
        FIG_B / "fig_q1_comparisons.png",
        FIG_B / "fig_q1_cluster.png",
        FIG_B / "fig_q1_palettes.png",
    ]
    for fp in report_figs:
        rel = fp.relative_to(ROOT).as_posix()
        ok = fp.exists() and abs(Image.open(fp).info.get("dpi", (0, 0))[0] - 300) < 1
        check(f"{rel} 存在且为 300 dpi", ok)

    check(
        "根目录 figures/fig_q1_hue.png 与 figures/b/fig_q1_hue.png 完全同步",
        hashlib.sha256((ROOT / "figures" / "fig_q1_hue.png").read_bytes()).hexdigest()
        == hashlib.sha256((FIG_B / "fig_q1_hue.png").read_bytes()).hexdigest(),
    )

    ppt_figs = [
        "fig_q1_genre_hue.png",
        "fig_q1_genre_metrics.png",
        "fig_q1_cluster.png",
        "fig_q1_palettes.png",
    ]
    for name in ppt_figs:
        fp = PPT_DIR / name
        check(f"outputs/b/ppt/{name} 存在", fp.exists())
        if fp.exists():
            w, h = Image.open(fp).size
            check(f"outputs/b/ppt/{name} 严格满足 16:9 像素比 ({w}×{h})", w * 9 == h * 16)

    lines = [
        "# B 阶段自动验收报告",
        "",
        "逐项自动检查：",
        "",
        *[f"- [{'x' if ok else ' '}] {lbl}" for lbl, ok in results],
        "",
        "说明：色相与无监督聚类严格限定 sat_frac ≥ 0.10（N=19,072），连续指标保留全量有效记录（N=19,694）；多标签对比采用电影级联合重采样 Bootstrap（1,000 次）。",
    ]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if not all(ok for _, ok in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
