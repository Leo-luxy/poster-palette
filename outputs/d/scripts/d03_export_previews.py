"""调用本机 PowerPoint COM 引擎将 docs/汇报.pptx 逐页导出为 1920x1080 高清预览图，供多模态视觉自审。"""
from pathlib import Path
import win32com.client

ROOT = Path(__file__).resolve().parents[3]
PPTX_PATH = ROOT / "docs" / "汇报.pptx"
OUT_DIR = ROOT / "outputs" / "d" / "slide_previews"


def main() -> None:
    if not PPTX_PATH.is_file():
        raise FileNotFoundError(f"未找到演示文稿：{PPTX_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("slide_*.png"):
        old.unlink()

    app = win32com.client.Dispatch("PowerPoint.Application")
    had_open = app.Presentations.Count > 0
    pres = None
    try:
        pres = app.Presentations.Open(str(PPTX_PATH), True, False, False)
        total = pres.Slides.Count
        for idx in range(1, total + 1):
            out_png = OUT_DIR / f"slide_{idx:02d}.png"
            pres.Slides(idx).Export(str(out_png), "PNG", 1920, 1080)
        print(f"已成功导出 {total} 页高清幻灯片预览至：{OUT_DIR}")
    finally:
        if pres is not None:
            pres.Close()
        if not had_open:
            app.Quit()


if __name__ == "__main__":
    main()
