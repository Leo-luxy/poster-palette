"""公共工具：输入审计、逐片色相归一、电影级联合 Bootstrap 与统一视觉配置。"""
from pathlib import Path
from datetime import datetime, timezone
import colorsys
import hashlib
import json
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import scipy
import sklearn
import matplotlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import common  # noqa: E402

OUT = ROOT / "outputs" / "b"
TABLES = OUT / "tables"
REPORTS = OUT / "reports"
PPT_DIR = OUT / "ppt"
FIG_B = ROOT / "figures" / "b"

INPUTS = ["movies.csv", "color_features.csv", "movie_details.csv", "yearly.csv"]
METRICS = ["mean_v", "mean_s", "colorful"]
HUE_COLS = [f"h{i}" for i in range(12)]
METRIC_LABELS = {"mean_v": "明度", "mean_s": "饱和度", "colorful": "色彩丰富度"}

PRESET_GENRES = ["科幻", "爱情", "恐怖"]
MAIN_GENRES = ["喜剧", "动画", "爱情", "剧情", "动作", "犯罪", "科幻", "惊悚", "恐怖"]
PALETTE_GENRES_8 = ["喜剧", "动画", "爱情", "剧情", "动作", "犯罪", "科幻", "恐怖"]
PPT_PALETTE_GENRES_4 = ["动画", "爱情", "科幻", "恐怖"]

CLUSTER_IDS = [0, 1, 2, 3]
CLUSTER_NAMES = {
    0: "明亮浅调",
    1: "浓烈暖调",
    2: "青蓝冷调",
    3: "深暗低彩",
}
CLUSTER_COLORS = {
    0: "#cbd5e1",
    1: "#dd6b20",
    2: "#2b6cb0",
    3: "#2d3748",
}

SEED = 42
BOOT_N = 1000
SAT_FRAC_MIN = 0.10
MIN_CELL = common.MIN_CELL

# 与 C 组完全统一的 12 扇区展示色标（仅表征色相扇区类别，不代表组内实际明暗）
HUE_COLORS = [colorsys.hsv_to_rgb((i + 0.5) / 12, 0.68, 0.88) for i in range(12)]

GENRE_COLOR = dict(common.COLOR)
GENRE_COLOR.setdefault("动画", "#805ad5")


def fingerprints() -> dict[str, str]:
    return {
        fname: hashlib.sha256((ROOT / "data" / fname).read_bytes()).hexdigest()
        for fname in INPUTS
    }


def load_safe(verify_manifest: bool = True) -> pd.DataFrame:
    """只读载入公共数据并执行主键、值域与输入指纹核验。"""
    TABLES.mkdir(parents=True, exist_ok=True)
    hashes = fingerprints()
    manifest_path = OUT / "run_manifest.json"
    if verify_manifest and manifest_path.exists():
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))["input_sha256"]
        if recorded != hashes:
            raise RuntimeError("输入数据 SHA-256 指纹与上次运行不一致，请核实版本后再执行。")

    m = pd.read_csv(ROOT / "data" / "movies.csv", dtype={"id": "int64"})
    f = pd.read_csv(ROOT / "data" / "color_features.csv", dtype={"tmdb_id": "int64"})
    d = pd.read_csv(ROOT / "data" / "movie_details.csv", dtype={"id": "int64"})

    for frame, key in [(m, "id"), (f, "tmdb_id"), (d, "id")]:
        if frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError(f"主键存在缺失或重复: {key}")

    m.loc[~m.id.isin(f.tmdb_id), ["id"]].to_csv(TABLES / "missing_features.csv", index=False, encoding="utf-8")
    f.loc[~f.tmdb_id.isin(m.id), ["tmdb_id"]].to_csv(TABLES / "orphan_features.csv", index=False, encoding="utf-8")

    x = (
        m.merge(f, left_on="id", right_on="tmdb_id", validate="one_to_one")
        .merge(d[["id", "production_countries"]], on="id", how="left", validate="one_to_one")
    )
    if len(x) != 19694 or not x.id.is_unique or not x.year.between(1950, 2025).all():
        raise RuntimeError(f"合并记录不符合预期基线：行数={len(x)}")

    x["decade"] = (x["year"] // 10 * 10).astype(int)
    x["genres"] = x["genre_ids"].astype(str).apply(
        lambda s: [common.GENRE.get(int(g), g) for g in s.split("|") if g and g != "nan"]
    )
    x.loc[x["genres"].apply(len) == 0, ["id", "title", "year"]].to_csv(
        TABLES / "missing_genres.csv", index=False, encoding="utf-8"
    )

    checks = []
    for col in METRICS + ["v_std", "sat_frac"]:
        vals = pd.to_numeric(x[col], errors="coerce")
        valid = vals[np.isfinite(vals)]
        upper_bad = (vals > 1.0) if col != "colorful" else False
        bad = (~np.isfinite(vals)) | (vals < 0.0) | upper_bad
        checks.append({
            "metric": col,
            "n_valid": int(len(valid)),
            "n_missing_or_nonfinite": int((~np.isfinite(vals)).sum()),
            "n_out_of_range": int((bad & np.isfinite(vals)).sum()),
            "min": float(valid.min()),
            "max": float(valid.max()),
        })
    pd.DataFrame(checks).to_csv(TABLES / "metric_audit.csv", index=False, encoding="utf-8")
    if any(c["n_out_of_range"] > 0 or c["n_missing_or_nonfinite"] > 0 for c in checks):
        raise ValueError("核心连续指标存在缺失或越界，详见 metric_audit.csv")

    return x


def eligible_hue_mask(frame: pd.DataFrame, sat_min: float = SAT_FRAC_MIN) -> np.ndarray:
    """判定色相有效样本：sat_frac >= sat_min 且 12 扇区非负有限、总和大于 0，且 hue 有效。"""
    h = frame[HUE_COLS].to_numpy(dtype=float)
    hue_col = pd.to_numeric(frame["hue"], errors="coerce").to_numpy(dtype=float)
    valid_h = np.isfinite(h).all(axis=1) & (h >= 0).all(axis=1) & (h.sum(axis=1) > 0) & np.isfinite(hue_col)
    return valid_h & (frame["sat_frac"].to_numpy(dtype=float) >= sat_min)


def bootstrap_1d(values: np.ndarray, seed: int = SEED, n_boot: int = BOOT_N) -> tuple[float, float, float, float]:
    """对单组电影独立重采样 n_boot 次，返回均值 95% CI 与中位数 95% CI。"""
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return (np.nan, np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    n = len(a)
    idx = rng.integers(0, n, size=(n_boot, n))
    samples = a[idx]
    means = samples.mean(axis=1)
    medians = np.median(samples, axis=1)
    return (
        float(np.percentile(means, 2.5)),
        float(np.percentile(means, 97.5)),
        float(np.percentile(medians, 2.5)),
        float(np.percentile(medians, 97.5)),
    )


def describe_group(frame: pd.DataFrame, bootstrap_ci: bool = True, seed: int = SEED) -> dict:
    """计算单组样本量、近灰比例及三项指标的均值/中位数/IQR/Bootstrap 95% CI。"""
    n_tot = len(frame)
    res: dict[str, float | int] = {
        "n_total": int(n_tot),
        "n_single_genre": int((frame["genres"].apply(len) == 1).sum()),
        "sat_frac_median": float(frame["sat_frac"].median()) if n_tot else np.nan,
        "near_gray_frac": float((frame["sat_frac"] < SAT_FRAC_MIN).sum() / n_tot) if n_tot else np.nan,
    }
    for m in METRICS:
        a = pd.to_numeric(frame[m], errors="coerce").to_numpy(dtype=float)
        a = a[np.isfinite(a)]
        res[f"{m}_n_valid"] = int(len(a))
        res[f"{m}_mean"] = float(np.mean(a)) if len(a) else np.nan
        res[f"{m}_median"] = float(np.median(a)) if len(a) else np.nan
        res[f"{m}_q1"] = float(np.percentile(a, 25)) if len(a) else np.nan
        res[f"{m}_q3"] = float(np.percentile(a, 75)) if len(a) else np.nan
        if bootstrap_ci:
            lo, hi, mlo, mhi = bootstrap_1d(a, seed=seed)
            res[f"{m}_mean_ci_low"] = lo
            res[f"{m}_mean_ci_high"] = hi
            res[f"{m}_median_ci_low"] = mlo
            res[f"{m}_median_ci_high"] = mhi
    return res


def hue_summary_group(frame: pd.DataFrame, group_label: str, sat_min: float = SAT_FRAC_MIN) -> dict:
    """逐片归一后按电影等权平均计算 12 扇区色相构成。"""
    good = eligible_hue_mask(frame, sat_min=sat_min)
    h = frame.loc[good, HUE_COLS].to_numpy(dtype=float)
    norm = h / h.sum(axis=1, keepdims=True)
    means = norm.mean(axis=0) if len(norm) else np.full(12, np.nan)
    row: dict[str, str | int | float] = {
        "group": str(group_label),
        "n_total": int(len(frame)),
        "n_hue": int(good.sum()),
        "near_gray_frac": float((frame["sat_frac"] < sat_min).sum() / len(frame)) if len(frame) else np.nan,
        "sat_frac_threshold": float(sat_min),
    }
    for i in range(12):
        row[f"h{i}"] = float(means[i])
    row["warm_0_60"] = float(means[0] + means[1]) if len(norm) else np.nan
    row["green_90_150"] = float(means[3] + means[4]) if len(norm) else np.nan
    row["cool_180_240"] = float(means[6] + means[7]) if len(norm) else np.nan
    return row


def joint_movie_contrast(
    values: np.ndarray,
    mask_a: np.ndarray,
    mask_b: np.ndarray,
    seed: int = SEED,
    n_boot: int = BOOT_N,
) -> dict[str, float | int]:
    """电影级联合重采样 Bootstrap（1部电影=1个独立抽样单元）。

    对多标签重叠组（如同时含科幻与恐怖的影片），在整库电影层面有放回抽样，
    每次同步重算两组的加权均值差，精确保留多标签重叠样本的协方差结构，避免伪重复计数偏差。
    """
    v = np.asarray(values, dtype=float)
    ma = np.asarray(mask_a, dtype=bool) & np.isfinite(v)
    mb = np.asarray(mask_b, dtype=bool) & np.isfinite(v)
    n_all = len(v)
    n_a = int(ma.sum())
    n_b = int(mb.sum())
    n_overlap = int((ma & mb).sum())
    diff_obs = float(v[ma].mean() - v[mb].mean())

    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=float)
    wa_base = ma.astype(float)
    wb_base = mb.astype(float)
    vw_a = np.where(ma, v, 0.0)
    vw_b = np.where(mb, v, 0.0)

    for b in range(n_boot):
        counts = np.bincount(rng.integers(0, n_all, size=n_all), minlength=n_all)
        sum_wa = float(np.dot(counts, wa_base))
        sum_wb = float(np.dot(counts, wb_base))
        mean_a = float(np.dot(counts, vw_a) / sum_wa)
        mean_b = float(np.dot(counts, vw_b) / sum_wb)
        diffs[b] = mean_a - mean_b

    return {
        "n_a": n_a,
        "n_b": n_b,
        "n_overlap": n_overlap,
        "mean_a": float(v[ma].mean()),
        "mean_b": float(v[mb].mean()),
        "mean_difference": diff_obs,
        "ci_low": float(np.percentile(diffs, 2.5)),
        "ci_high": float(np.percentile(diffs, 97.5)),
    }


def save_manifest() -> None:
    def git_cmd(*args: str) -> str | None:
        p = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return p.stdout.strip() if p.returncode == 0 else None

    payload = {
        "input_sha256": fingerprints(),
        "git_commit": git_cmd("rev-parse", "HEAD"),
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "config": {
            "seed": SEED,
            "bootstrap_iterations": BOOT_N,
            "bootstrap_unit": "joint_movie_level_resampling",
            "sat_frac_min": SAT_FRAC_MIN,
            "min_cell": MIN_CELL,
            "preset_genres": PRESET_GENRES,
            "main_genres": MAIN_GENRES,
            "cluster_feature_space": "Conic_5D [mean_v, mean_s, colorful, mean_s*cos(hue), mean_s*sin(hue)]",
            "cluster_k": 4,
            "cluster_names": CLUSTER_NAMES,
        },
        "run_utc": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def apply_plot_rc() -> None:
    matplotlib.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "PingFang SC", "Arial Unicode MS", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
        "savefig.facecolor": "white",
    })
