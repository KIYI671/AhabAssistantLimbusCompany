"""User supplied gift artwork: portable imports and local icon matching, without OCR."""

import hashlib
import math
import re
import shutil
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def import_gift_image(source, folder="assets/user/gift_protection"):
    source = Path(source)
    with Image.open(source) as image:
        image.verify()
    with Image.open(source) as image:
        if min(image.size) < 12 or max(image.size) > 8192:
            raise ValueError("请添加至少12像素、至多8192像素的饰品图标")
        extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "BMP": ".bmp"}.get(image.format)
        if extension is None:
            raise ValueError("支持 PNG、WEBP、JPG、BMP 图片")
        if image.convert("RGBA").getchannel("A").getbbox() is None:
            raise ValueError("图片完全透明")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:20]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", source.stem)[:50]
    destination = Path(folder) / f"{digest}_{name}{extension}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    return destination.as_posix()


@lru_cache(maxsize=128)
def _variants(path, modified, height):
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        rgba = rgba.crop(rgba.getchannel("A").getbbox())
        variants = []
        # An imported screenshot already has a meaningful pixel size. Never
        # discard it merely because it falls outside the preset game sizes.
        widths = dict.fromkeys([
            rgba.width,
            max(16, round(rgba.width * height / 1080)),
            *(max(16, round(w * height / 1080)) for w in range(48, 257, 4)),
        ])
        for width in widths:
            size = (width, max(12, round(width * rgba.height / rgba.width)))
            resized = np.asarray(rgba.resize(size, Image.Resampling.LANCZOS))
            gray = cv2.cvtColor(resized[:, :, :3], cv2.COLOR_RGB2GRAY)
            mask = (resized[:, :, 3] >= 180).astype(np.uint8) * 255
            if np.count_nonzero(mask) >= 30 and np.std(gray[mask > 0]) > 3:
                # Opaque screenshots do not need the much slower masked
                # correlation path. Preserve masking for transparent artwork.
                variants.append((gray, None if np.all(mask) else mask))
        if not variants:
            raise ValueError(f"保护图片没有可识别图案：{Path(path).name}")
        return tuple(variants)


class ProtectedGiftMatcher:
    def __init__(self, paths, threshold=0.80):
        self.paths = tuple(paths)
        self.threshold = threshold
        self.last_scan = None

    def match(self, screenshot, point):
        if not self.paths:
            return None
        image = np.asarray(screenshot.convert("L"))
        height, width = image.shape
        scale = height / 1440
        x, y = point
        tolerance = 95 * scale
        self.last_scan = {"point": tuple(point), "screenshot": (width, height),
                          "score": None, "path": None, "size": None, "center": None}
        for path in self.paths:
            stat = Path(path).stat()  # Missing/invalid references fail closed in the shop adapter.
            for gray, mask in _variants(path, stat.st_mtime_ns, height):
                th, tw = gray.shape
                # Restrict *centres*, while including the entire template in
                # the crop. The former fixed-radius crop truncated large icons
                # and icons clicked near their edge/badge. A neighbouring icon
                # outside this centre window must not hide a valid local match.
                left = max(0, math.ceil(x - tolerance - tw / 2))
                top = max(0, math.ceil(y - tolerance - th / 2))
                last_x = min(width - tw, math.floor(x + tolerance - tw / 2))
                last_y = min(height - th, math.floor(y + tolerance - th / 2))
                if last_x < left or last_y < top:
                    continue
                crop = image[top:last_y + th, left:last_x + tw]
                result = cv2.matchTemplate(crop, gray, cv2.TM_CCOEFF_NORMED, mask=mask)
                result = np.nan_to_num(result, nan=-1, posinf=-1, neginf=-1)
                _, score, _, location = cv2.minMaxLoc(result)
                cx, cy = left + location[0] + tw / 2, top + location[1] + th / 2
                if self.last_scan["score"] is None or score > self.last_scan["score"]:
                    self.last_scan.update(score=float(score), path=path, size=(tw, th), center=(cx, cy))
                if score >= self.threshold:
                    return path
        return None

    def find_in_region(self, screenshot, bounds, excluded_paths=()):
        """Find a configured icon only in the merchant's stock rectangle."""
        image = np.asarray(screenshot.convert("L"))
        height, width = image.shape
        left, top, right, bottom = (round(v) for v in bounds)
        left, top, right, bottom = max(0, left), max(0, top), min(width, right), min(height, bottom)
        if right <= left or bottom <= top:
            return None
        region = image[top:bottom, left:right]
        for path in self.paths:
            if path in excluded_paths:
                continue
            stat = Path(path).stat()
            for gray, mask in _variants(path, stat.st_mtime_ns, height):
                th, tw = gray.shape
                if th > region.shape[0] or tw > region.shape[1]:
                    continue
                match = cv2.matchTemplate(region, gray, cv2.TM_CCOEFF_NORMED, mask=mask)
                match = np.nan_to_num(match, nan=-1, posinf=-1, neginf=-1)
                _, score, _, point = cv2.minMaxLoc(match)
                if score >= self.threshold:
                    center = left + point[0] + tw / 2, top + point[1] + th / 2
                    self.last_scan = dict(path=path, score=float(score), center=center, size=(tw, th),
                                          screenshot=(width, height), region=(left, top, right, bottom))
                    return path, center
        return None
