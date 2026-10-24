"""Direct corrosion-animation recognition, including lower-corner TOTAL."""

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@lru_cache(maxsize=1)
def _banner():
    with Image.open(Path("assets/app/faust_battle/overclock_banner.png")) as image:
        return image.convert("L").copy()


@lru_cache(maxsize=4)
def _scaled_banners(height):
    reference = _banner()
    # Try the expected size first; cache resampling across animation frames.
    factors = sorted((.8 + step * .025 for step in range(17)), key=lambda value: abs(value - 1))
    return tuple(np.array(reference.resize(
        (round(reference.width * height / 1060 * factor), round(reference.height * height / 1060 * factor)),
        Image.Resampling.LANCZOS)) for factor in factors)


def visual_overclock(auto):
    if not hasattr(auto.screenshot, "convert"):
        return False
    image = auto.screenshot.convert("L")
    width, height = image.size
    region = np.array(image.crop((int(width * 0.25), 0, int(width * 0.75), int(height * 0.27))))
    for template in _scaled_banners(height):
        if template.shape[1] > region.shape[1] or template.shape[0] > region.shape[0]:
            continue
        if cv2.minMaxLoc(cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED))[1] >= 0.72:
            return True
    return False


def total_marker(auto):
    width, height = auto.screenshot.size
    for left, right in ((0.62, 1), (0, 0.38)):
        words = auto._run_ocr_for_text(
            my_crop=(int(width * left), int(height * 0.72), int(width * right), height), only_text=True
        )
        letters = "".join(c for c in "".join(words or []).upper() if c.isalpha())
        if "TOTAL" in letters:
            return True
    return False


def corner_play_marker(auto):
    """Find a small, filled, right-pointing white triangle in any corner."""
    if not hasattr(auto.screenshot, "convert"):
        return False
    picture = np.array(auto.screenshot.convert("RGB"))
    height, width = picture.shape[:2]
    scale = height / 1080
    for x0, y0 in ((0, 0), (int(width * 0.84), 0), (0, int(height * 0.8)),
                   (int(width * 0.84), int(height * 0.8))):
        region = picture[y0:min(height, y0 + int(height * 0.2)), x0:min(width, x0 + int(width * 0.16))]
        # Color saturation excludes warning-red triangles. Brightness and
        # contour shape exclude most text, rectangular buttons and outlines.
        white = ((region.min(axis=2) >= 205) & (np.ptp(region.astype(np.int16), axis=2) <= 35))
        mask = white.astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if not (8 * scale <= w <= 58 * scale and 10 * scale <= h <= 70 * scale and 0.45 <= w / h <= 1.35):
                continue
            polygon = cv2.approxPolyDP(contour, 0.055 * cv2.arcLength(contour, True), True)
            if len(polygon) != 3 or not cv2.isContourConvex(polygon):
                continue
            area = cv2.contourArea(contour)
            if area <= 0 or cv2.countNonZero(mask[y:y + h, x:x + w]) / area < 0.75:
                continue
            points = polygon[:, 0, :]
            tip = points[np.argmax(points[:, 0])]
            base = points[np.argsort(points[:, 0])[:2]]
            if (abs(int(base[0, 0]) - int(base[1, 0])) <= w * 0.2
                    and abs(float(tip[1]) - float(base[:, 1].mean())) <= h * 0.2
                    and tip[0] - base[:, 0].mean() >= w * 0.7
                    and area >= w * h * 0.32):
                return True
    return False
