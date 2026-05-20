import os
import sys
import time
from ctypes import c_void_p, windll
from pathlib import Path


# =============================================================================
# 初始化区域：DPI、项目路径、依赖导入、参数、Steam 游戏窗口、截图
# =============================================================================

# DPI awareness must be set before importing Win32 / screenshot-related modules.
try:
    if not windll.user32.SetProcessDpiAwarenessContext(c_void_p(-4)):
        raise OSError
except Exception:
    try:
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import cv2
import numpy as np
from PIL import Image

from module.automation.screenshot import ScreenShot
from module.config import cfg
from module.game_and_screen import game_process, screen
from utils.image_utils import ImageUtils

game_process.start_game()
deadline = time.time() + 120
while not screen.init_handle():
    if time.time() > deadline:
        raise RuntimeError("120 秒内未识别到 Steam 端游戏窗口")
    time.sleep(3)

screenshot = ScreenShot.take_screenshot(gray=False)
if screenshot is None:
    raise RuntimeError("截图失败")

screenshot_path = PROJECT_ROOT / "screenshot.png"
screenshot.save(screenshot_path)
screenshot_gray = np.array(screenshot.convert("L"))
screen_h, screen_w = screenshot_gray.shape[:2]
scale = screen_h / 1440

print(f"game_process={cfg.game_process_name}")
print(f"game_title={cfg.game_title_name}")
print(f"hwnd={screen.handle.hwnd}")
print(f"monitor={screen.handle.monitor_size(False)}")
print(f"work={screen.handle.monitor_size(True)}")
print(f"client={screen.handle.width(True)}x{screen.handle.height(True)}")
print(f"screenshot={screen_w}x{screen_h}")
print(f"screenshot_path={screenshot_path}")
print(f"scale={scale:.6f}")

# 到这里初始化已经完成。
# 你可以在这里插入其他测试代码，例如 OCR、窗口尺寸验证、点击坐标验证等。

# =============================================================================
# 核心识图区域：扫描 assets/images 下的目标图片，并计算模板匹配相似度
# =============================================================================

image_root = PROJECT_ROOT / "assets" / "images"
target = "lunacy_spend_26_assets.png"
threshold = 0.8
models = ("clam", "normal")

print(f"target={target}")
print(f"threshold={threshold}")
print("model=both")

image_files = sorted(image_root.glob(f"**/{target}"))
if not image_files:
    raise RuntimeError(f"未找到任何目标图片: {image_root.as_posix()}/**/{target}")

results = []
for image_file in image_files:
    with Image.open(image_file) as image:
        template_full = np.array(image)

    if template_full.ndim == 3 and template_full.shape[2] > 3:
        template_full = template_full[:, :, :3]
    if template_full.ndim == 3:
        template_full = cv2.cvtColor(template_full, cv2.COLOR_RGB2GRAY)

    template_full = cv2.resize(
        template_full,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )

    bbox = ImageUtils.get_bbox(template_full)
    template = ImageUtils.crop(template_full, bbox)
    relative_path = image_file.relative_to(image_root).as_posix()

    for model in models:
        center, score = ImageUtils.match_template(screenshot_gray, template, bbox, model=model)
        results.append(
            (
                float(score),
                model,
                relative_path,
                tuple(int(v) for v in center),
                tuple(int(v) for v in bbox),
            )
        )

results.sort(reverse=True, key=lambda item: item[0])

print()
print("匹配结果:")
for score, model, relative_path, center, bbox in results:
    print(f"{relative_path}, {model}: score={score:.6f}, center={center}, bbox={bbox}, matched={score >= threshold}")

best = results[0]
print()
print(f"最高匹配: image={best[2]}, model={best[1]}, score={best[0]:.6f}, center={best[3]}, matched={best[0] >= threshold}")
