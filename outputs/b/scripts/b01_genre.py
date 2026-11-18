"""做法 A：电影类型的配色结构、预定对比差值（电影级联合 Bootstrap）与稳健性检验。"""
import numpy as np
import pandas as pd
from scipy.stats import kruskal

from b_common import (
    common,
    HUE_COLS,
    MAIN_GENRES,
    METRICS,
    PRESET_GENRES,
    SAT_FRAC_MIN,
    SEED,
    TABLES,
    describe_group,
    eligible_hue_mask,
    hue_summary_group,
    joint_movie_contrast,
    load_safe,
    save_manifest,
)

SECTOR_LABELS = [
    "0°–30° 红", "30°–60° 橙黄", "60°–90° 黄", "90°–120° 黄绿",
    "120°–150° 绿", "150°–180° 青绿", "180°–210° 青", "210°–240° 蓝",
    "240°–270° 蓝紫", "270°–300° 紫", "300°–330° 品红", "330°–360° 红紫",
]


def main() -> None:
    save_manifest()
    x = load_safe(verify_manifest=True)

    pd.DataFrame([
        {
            "sector": f"h{i}",
            "start_degrees": 30 * i,
            "end_degrees_exclusive": 30 * (i + 1),
            "label": SECTOR_LABELS[i],
        }
        for i in range(12)
    ]).to_csv(TABLES / "hue_sectors.csv", index=False, encoding="utf-8")

    # 1. 9 大核心类型 + 全库基线汇总表与色相表
    summary_rows = []
    hue_rows = []
    for g in MAIN_GENRES:
        sub = x[common.has_genre(x, g)]
        summary_rows.append({"genre": g, **describe_group(sub, bootstrap_ci=True, seed=SEED)})
        hue_rows.append(hue_summary_group(sub, g, sat_min=SAT_FRAC_MIN))

    summary_rows.append({"genre": "ALL", **describe_group(x, bootstrap_ci=True, seed=SEED)})
    hue_rows.append(hue_summary_group(x, "ALL", sat_min=SAT_FRAC_MIN))

    pd.DataFrame(summary_rows).to_csv(TABLES / "genre_summary.csv", index=False, encoding="utf-8")
    pd.DataFrame(hue_rows).to_csv(TABLES / "genre_hue.csv", index=False, encoding="utf-8")

    # 2. 全部 19 个类型的完整汇总表（供查阅与附录核对）
    all_genre_rows = []
    for _, gname in sorted(common.GENRE.items()):
        sub = x[common.has_genre(x, gname)]
        desc = describe_group(sub, bootstrap_ci=True, seed=SEED)
        hue_d = hue_summary_group(sub, gname, sat_min=SAT_FRAC_MIN)
        all_genre_rows.append({
            "genre": gname,
            **desc,
            "n_hue": hue_d["n_hue"],
            "warm_0_60": hue_d["warm_0_60"],
            "green_90_150": hue_d["green_90_150"],
            "cool_180_240": hue_d["cool_180_240"],
            **{f"h{i}": hue_d[f"h{i}"] for i in range(12)},
        })
    all_df = pd.DataFrame(all_genre_rows).sort_values("n_total", ascending=False)
    all_df.to_csv(TABLES / "genre_summary_all.csv", index=False, encoding="utf-8")

    # 3. 逐片归一色相特征向量（供电影级联合 Bootstrap 对比使用）
    good_h = eligible_hue_mask(x, sat_min=SAT_FRAC_MIN)
    h_raw = x[HUE_COLS].to_numpy(dtype=float)
    h_norm = np.full_like(h_raw, np.nan, dtype=float)
    h_norm[good_h] = h_raw[good_h] / h_raw[good_h].sum(axis=1, keepdims=True)

    hue_band_series = {
        "warm_0_60": h_norm[:, 0] + h_norm[:, 1],
        "green_90_150": h_norm[:, 3] + h_norm[:, 4],
        "cool_180_240": h_norm[:, 6] + h_norm[:, 7],
    }

    genre_masks = {g: common.has_genre(x, g).to_numpy(dtype=bool) for g in MAIN_GENRES}
    all_mask = np.ones(len(x), dtype=bool)

    # 4. 预定对比：主讲三类两两对比 + 9 大类型减全库均值
    contrasts = []
    preset_pairs = [("爱情", "恐怖"), ("爱情", "科幻"), ("科幻", "恐怖")]
    for ga, gb in preset_pairs:
        for m in METRICS:
            res = joint_movie_contrast(x[m].to_numpy(dtype=float), genre_masks[ga], genre_masks[gb], seed=SEED)
            contrasts.append({"contrast_type": "preset_pair", "group_a": ga, "group_b": gb, "metric": m, **res})
        for band_name, band_vals in hue_band_series.items():
            res = joint_movie_contrast(band_vals, genre_masks[ga], genre_masks[gb], seed=SEED)
            contrasts.append({"contrast_type": "preset_pair", "group_a": ga, "group_b": gb, "metric": band_name, **res})

    for g in MAIN_GENRES:
        for m in METRICS:
            res = joint_movie_contrast(x[m].to_numpy(dtype=float), genre_masks[g], all_mask, seed=SEED)
            contrasts.append({"contrast_type": "vs_all", "group_a": g, "group_b": "ALL", "metric": m, **res})
        for band_name, band_vals in hue_band_series.items():
            res = joint_movie_contrast(band_vals, genre_masks[g], all_mask, seed=SEED)
            contrasts.append({"contrast_type": "vs_all", "group_a": g, "group_b": "ALL", "metric": band_name, **res})

    pd.DataFrame(contrasts).to_csv(TABLES / "genre_contrasts.csv", index=False, encoding="utf-8")

    # 5. 稳健性与敏感性检验
    sens_rows = []

    # (a) 屏蔽 0°–60°（红橙黄/肤色高发区）后在单张海报内重归一 60°–360° 扇区
    rem_sum = np.nansum(h_norm[:, 2:], axis=1)
    valid_noskin = good_h & (rem_sum >= 0.05)
    noskin_norm = np.full((len(x), 10), np.nan, dtype=float)
    noskin_norm[valid_noskin] = h_norm[valid_noskin, 2:] / rem_sum[valid_noskin, None]
    # noskin_norm 索引: 2->h4(120-150°绿), 4->h6(180-210°青), 5->h7(210-240°蓝), 8->h10, 9->h11(300-360°品红/红紫)
    cool_noskin = noskin_norm[:, 4] + noskin_norm[:, 5]
    green_noskin = noskin_norm[:, 1] + noskin_norm[:, 2]  # 90-150°

    for ga, gb, arr, label in [
        ("科幻", "爱情", cool_noskin, "cool_180_240_noskin"),
        ("科幻", "恐怖", cool_noskin, "cool_180_240_noskin"),
        ("恐怖", "爱情", green_noskin, "green_90_150_noskin"),
    ]:
        res = joint_movie_contrast(arr, genre_masks[ga], genre_masks[gb], seed=SEED)
        sens_rows.append({
            "check_family": "skin_sector_exclusion_0_60",
            "setting": f"{ga}_minus_{gb}",
            "metric": label,
            "n_a": res["n_a"],
            "n_b": res["n_b"],
            "estimate": res["mean_difference"],
            "ci_low": res["ci_low"],
            "ci_high": res["ci_high"],
            "aux_stat": np.nan,
            "p_value": np.nan,
        })

    # 同时输出三类在屏蔽 0-60° 后的自身均值占比供绘图直接读取
    for g in PRESET_GENRES + ["ALL"]:
        m_g = all_mask if g == "ALL" else genre_masks[g]
        mk = m_g & valid_noskin
        lo_c, hi_c, _, _ = (
            joint_movie_contrast(cool_noskin, m_g, m_g, seed=SEED)["mean_a"],
            0.0, 0.0, 0.0
        )
        # 单组均值及 Bootstrap 95% CI
        from b_common import bootstrap_1d
        c_lo, c_hi, _, _ = bootstrap_1d(cool_noskin[mk], seed=SEED)
        g_lo, g_hi, _, _ = bootstrap_1d(green_noskin[mk], seed=SEED)
        sens_rows.append({
            "check_family": "skin_sector_group_level",
            "setting": g,
            "metric": "cool_180_240_noskin",
            "n_a": int(mk.sum()),
            "n_b": int(m_g.sum()),
            "estimate": float(np.mean(cool_noskin[mk])),
            "ci_low": c_lo,
            "ci_high": c_hi,
            "aux_stat": np.nan,
            "p_value": np.nan,
        })
        sens_rows.append({
            "check_family": "skin_sector_group_level",
            "setting": g,
            "metric": "green_90_150_noskin",
            "n_a": int(mk.sum()),
            "n_b": int(m_g.sum()),
            "estimate": float(np.mean(green_noskin[mk])),
            "ci_low": g_lo,
            "ci_high": g_hi,
            "aux_stat": np.nan,
            "p_value": np.nan,
        })

    # (b) sat_frac 阈值扫描 (0.05, 0.10, 0.15, 0.20)
    for th in [0.05, 0.10, 0.15, 0.20]:
        mk_th = eligible_hue_mask(x, sat_min=th)
        hn = np.full((len(x), 12), np.nan, dtype=float)
        hn[mk_th] = h_raw[mk_th] / h_raw[mk_th].sum(axis=1, keepdims=True)
        for ga, gb, vec, mname in [
            ("爱情", "恐怖", hn[:, 0] + hn[:, 1], "warm_0_60"),
            ("科幻", "爱情", hn[:, 6] + hn[:, 7], "cool_180_240"),
            ("恐怖", "爱情", hn[:, 3] + hn[:, 4], "green_90_150"),
        ]:
            res = joint_movie_contrast(vec, genre_masks[ga], genre_masks[gb], seed=SEED)
            sens_rows.append({
                "check_family": "sat_frac_threshold_scan",
                "setting": f"sat_frac>={th:.2f}_{ga}_minus_{gb}",
                "metric": mname,
                "n_a": res["n_a"],
                "n_b": res["n_b"],
                "estimate": res["mean_difference"],
                "ci_low": res["ci_low"],
                "ci_high": res["ci_high"],
                "aux_stat": float(mk_th.sum()),
                "p_value": np.nan,
            })

    # (c) 严格互斥三类子集（剔除同时含科幻/爱情/恐怖两个及以上标签的重叠片）的 Kruskal-Wallis 检验
    m_sf, m_ro, m_ho = genre_masks["科幻"], genre_masks["爱情"], genre_masks["恐怖"]
    only_sf = m_sf & (~m_ro) & (~m_ho)
    only_ro = m_ro & (~m_sf) & (~m_ho)
    only_ho = m_ho & (~m_sf) & (~m_ro)
    for m in METRICS:
        vals = x[m].to_numpy(dtype=float)
        g1, g2, g3 = vals[only_sf], vals[only_ro], vals[only_ho]
        h_stat, p_val = kruskal(g1, g2, g3)
        n_disjoint = len(g1) + len(g2) + len(g3)
        eta_sq = float((h_stat - 3 + 1) / (n_disjoint - 3))
        sens_rows.append({
            "check_family": "disjoint_preset_kruskal",
            "setting": "科幻_only_vs_爱情_only_vs_恐怖_only",
            "metric": m,
            "n_a": int(len(g2)),   # 爱情互斥片数
            "n_b": int(len(g3)),   # 恐怖互斥片数
            "estimate": float(g2.mean() - g3.mean()),
            "ci_low": np.nan,
            "ci_high": np.nan,
            "aux_stat": float(h_stat),
            "p_value": float(p_val),
            "eta_squared_h": eta_sq,
            "n_disjoint_total": int(n_disjoint),
        })

    pd.DataFrame(sens_rows).to_csv(TABLES / "sensitivity_checks.csv", index=False, encoding="utf-8")
    print(f"做法 A 完成：全库 {len(x):,} 部，色相有效 {int(good_h.sum()):,} 部，对比与稳健性表已写出。")


if __name__ == "__main__":
    main()
