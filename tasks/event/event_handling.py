import time

from module.automation import auto
from module.config import cfg


class EventHandling:
    MAX_CHANGE = -1

    def __init__(self):
        self.change_mode = self.MAX_CHANGE
        self.time = time.time() - 15
        self.times = 0

    def decision_event_handling(self):
        if best_option := auto.find_element("event/very_high.png"):
            auto.mouse_action_with_pos(best_option)
            self.change_mode = self.MAX_CHANGE
        elif best_option := auto.find_element("event/high.png"):
            auto.mouse_action_with_pos(best_option)
            self.change_mode = self.MAX_CHANGE
        elif best_option := auto.find_element("event/normal.png"):
            auto.mouse_action_with_pos(best_option)
            self.change_mode = self.MAX_CHANGE
        elif best_option := auto.find_element("event/low.png"):
            auto.mouse_action_with_pos(best_option)
            self.change_mode = self.MAX_CHANGE
        elif best_option := auto.find_element("event/very_low.png"):
            auto.mouse_action_with_pos(best_option)
            self.change_mode = self.MAX_CHANGE
        else:
            if self.change_mode >= 0:
                self.change_mode -= 1
            else:
                self.decision_event_handling_ocr()

    def decision_event_handling_ocr(self):
        now_time = time.time()
        if now_time - self.time < 15:
            self.time = now_time
            self.times += 1
        else:
            self.times = 0
        ocr_data = auto.find_text_element("", only_text=True)
        ocr_result = extract_levels(ocr_data)
        try:
            order = ocr_result.index("very high")
        except:
            try:
                order = ocr_result.index("high")
            except:
                try:
                    order = ocr_result.index("normal")
                except:
                    try:
                        order = ocr_result.index("low")
                    except:
                        order = ocr_result.index("very low")
        scale = cfg.set_win_size / 1440
        first_sinner = [150 * scale, 1300 * scale]
        target_sinner = [first_sinner[0] + 140 * (order + self.times) * scale, first_sinner[1]]
        auto.mouse_click(target_sinner[0], target_sinner[1])


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
    exact_match = {'low': 'low'}
    fuzzy_match = {
        'veryhigh': 'very high',
        'high': 'high',
        'normal': 'normal',
        'verylow': 'very low'
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

                    substr = s[i:i + sub_len]
                    if is_edit_distance_one(substr, level_str):
                        levels.append(level_name)
                        i += sub_len
                        matched = True
                        break

                if matched:
                    break

            if not matched:
                i += 1  # 没有匹配，移动一个字符

    return levels
