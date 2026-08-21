import time

from module.automation import auto
from module.config import cfg
from module.logger import log


class EventHandling:
    SUCCESS_LEVEL_ASSETS = (
        "event/very_high.png",
        "event/high.png",
        "event/normal.png",
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
        for asset in self.SUCCESS_LEVEL_ASSETS:
            if best_option := auto.find_element(asset, threshold=self.SUCCESS_LEVEL_THRESHOLD):
                auto.mouse_action_with_pos(best_option)
                self.last_action_time = now
                self.fallback_offset = 0
                return True

        return self.decision_event_handling_ocr(now=now)

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
