import time

import cv2
import numpy as np
from PIL import Image

from module.automation import auto
from module.config import cfg
from module.logger import log
from utils.image_utils import ImageUtils


class EventHandling:
    # 高概率的成功系
    SUCCESS_LEVEL_ASSETS = (
        "event/very_high.png",
        "event/high.png",
        "event/normal.png",
    )
    # 低概率的红色（失败）系
    WARN_LEVEL_ASSETS = (
        "event/low.png",
        "event/very_low.png",
    )
    SUCCESS_LEVEL_PRIORITY = ("very high", "high", "normal", "low", "very low")
    SUCCESS_LEVEL_THRESHOLD = 0.74
    ACTION_RETRY_INTERVAL = 0.75
    SINNER_COUNT = 12

    def __init__(self):
        self.last_action_time = float("-inf")
        self.fallback_offset = 0

    def _can_retry(self, now: float) -> bool:
        return now - self.last_action_time >= self.ACTION_RETRY_INTERVAL

    def decision_event_handling(self) -> bool:
        """选择成功率最高的罪人；模板和 OCR 都失败时仍能安全轮换兜底。"""
        now = time.monotonic()
        if not self._can_retry(now):
            return False

        # 该方法只在“选择罪人进行判定”特征已命中后调用，因此可以使用稍低的
        # 专用阈值，兼容 MuMu 缩放后落在默认 0.8 临界线下方的彩色成功率文字。
        # 彩色截图 → 罪人区域内红色（低/极低）涂黑 → 转灰度 → 找极高/高/一般，
        # 这样very low不会再被灰度匹配误判成极高。
        if auto.take_screenshot(gray=False) is not None:
            frame = np.array(auto.screenshot)
            if (bbox_img := ImageUtils.load_image("event/all_sinner_bbox.png")) is not None:
                black_out_red(frame, ImageUtils.get_bbox(bbox_img))
            auto.screenshot = Image.fromarray(frame).convert("L")
            if self._click_first_hit(self.SUCCESS_LEVEL_ASSETS, now):
                return True

        # 极高/高/一般三档都没命中：重新截屏（不再处理红色部分），按原流程找低/极低
        auto.take_screenshot()
        if self._click_first_hit(self.WARN_LEVEL_ASSETS, now):
            return True

        return self.decision_event_handling_ocr(now=now)

    def _click_first_hit(self, assets, now: float) -> bool:
        for asset in assets:
            if best_option := auto.find_element(asset, threshold=self.SUCCESS_LEVEL_THRESHOLD):
                auto.mouse_action_with_pos(best_option)
                self.last_action_time = now
                self.fallback_offset = 0
                return True
        return False

    def decision_event_handling_ocr(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if not self._can_retry(now):
            return False

        order = 0
        try:
            ocr_data = auto.find_text_element("", only_text=True)
            levels = extract_levels(ocr_data or [])
            order = next(
                (levels.index(level) for level in self.SUCCESS_LEVEL_PRIORITY if level in levels),
                0,
            )
            if not levels:
                log.debug("OCR未识别到事件成功率，轮换点击底部罪人作为兜底")
        except Exception as e:
            msg = f"OCR识别事件成功率失败，错误信息：{e}"
            log.debug(msg)

        scale = cfg.set_win_size / 1440
        sinner_index = (order + self.fallback_offset) % self.SINNER_COUNT
        target_sinner = [
            (150 + 140 * sinner_index) * scale,
            1300 * scale,
        ]
        auto.mouse_click(target_sinner[0], target_sinner[1])
        self.last_action_time = now
        self.fallback_offset = (self.fallback_offset + 1) % self.SINNER_COUNT
        return True

    def click_option_avoiding_unknown(self) -> bool:
        """小指良单通模式：事件选项出现“？？？”时，改为选择其它选项。"""
        unknown_pos = auto.find_element("event/unknown_event.png")
        if not unknown_pos:
            return False
        positions = auto.find_element(
            "event/select_first_option_assets.png",
            find_type="image_with_multiple_targets",
            threshold=0.75,
        )
        if not positions:
            return False
        # “？？？”标签画在所属选项按钮内部，按钮自上而下排列：
        # 所属按钮取标签上方最近的按钮（都不在上方时退回最近的），改选离标签最近的其它按钮
        above = [p for p in positions if p[1] <= unknown_pos[1]]
        owner = max(above, key=lambda p: p[1]) if above else min(positions, key=lambda p: abs(p[1] - unknown_pos[1]))
        others = [p for p in positions if p is not owner]
        target = min(others, key=lambda p: abs(p[1] - unknown_pos[1])) if others else owner
        log.info("小指良单通模式：跳过“？？？”选项，规避诅咒饰品")
        auto.mouse_click(target[0], target[1])
        return True


def black_out_red(frame_rgb, bbox):
    """把 bbox 内红色系像素（低/极低徽章）置黑，使其不再干扰金橙系等级匹配。

    只抹高饱和红（H≈1°，OpenCV 8bit H=角度/2 即 ≤4 或 ≥175）：金橙系徽章
    （极高/高/一般）H≈18~23°，不会被抹。bbox 外区域保持原样。
    """
    roi = frame_rgb[bbox[1] : bbox[3], bbox[0] : bbox[2]]
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    red = ((hsv[:, :, 0] <= 4) | (hsv[:, :, 0] >= 175)) & (hsv[:, :, 1] >= 90)
    roi[red] = 0


def is_edit_distance_one(s1, s2):
    """检查两个字符串的编辑距离是否为1（允许插入、删除或替换一个字符）"""
    len1, len2 = len(s1), len(s2)
    if abs(len1 - len2) > 1:
        return False

    if len1 == len2:
        # 检查替换一个字符的情况
        diff = 0
        for c1, c2 in zip(s1, s2):
            if c1 != c2:
                diff += 1
                if diff > 1:
                    return False
        return diff == 1

    # 确保s1是较短的字符串
    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    # 检查插入/删除一个字符的情况
    i = j = 0
    while i < len1 and j < len2:
        if s1[i] == s2[j]:
            i += 1
        else:
            if j > i:  # 已经有过一次跳过
                return False
            j += 1  # 跳过s2中多余的字符
            continue
        j += 1

    # 如果最后还有剩余字符
    remaining = len2 - j
    return remaining <= 1


def extract_levels(data):
    """从OCR数据中提取级别信息，对"low"只进行精确匹配"""
    # 定义级别映射（区分精确匹配和模糊匹配）
    exact_match = {"low": "low"}
    fuzzy_match = {
        "veryhigh": "very high",
        "high": "high",
        "normal": "normal",
        "verylow": "very low",
    }

    levels = []

    for item in data:
        s = str(item).lower().replace(" ", "")  # 转为小写并移除空格

        i = 0
        while i < len(s):
            matched = False

            # 1. 先尝试精确匹配（特别是"low"）
            for level_str, level_name in exact_match.items():
                if s.startswith(level_str, i):
                    levels.append(level_name)
                    i += len(level_str)
                    matched = True
                    break

            if matched:
                continue

            # 2. 尝试模糊匹配（允许一位错误或缺失）
            for level_str, level_name in fuzzy_match.items():
                # 尝试不同长度的子串（原长度±1）
                for sub_len in [len(level_str) - 1, len(level_str), len(level_str) + 1]:
                    if sub_len <= 0 or i + sub_len > len(s):
                        continue

                    substr = s[i : i + sub_len]
                    if substr == level_str or is_edit_distance_one(substr, level_str):
                        levels.append(level_name)
                        i += sub_len
                        matched = True
                        break

                if matched:
                    break

            if not matched:
                i += 1  # 没有匹配，移动一个字符

    return levels
