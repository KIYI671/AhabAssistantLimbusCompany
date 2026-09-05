"""
图像差异计算工具 - 检测画面跳变替代固定 sleep

提供基于像素级差异和感知哈希的画面变化检测，适用于：
- 等待加载动画结束（画面从变动→稳定）
- 等待按钮/弹窗出现（画面从A→B）
- 替代固定 sleep() 的保守等待

依赖：PIL, numpy（均为 AALC 已有依赖）
"""

import time
from typing import Optional, Callable

import numpy as np
from PIL import Image, ImageChops


class ImageDiff:
    """图像差异计算工具"""

    @staticmethod
    def calculate_diff_ratio(img1: Image.Image, img2: Image.Image) -> float:
        """
        计算两张图像的差异度（0~1）

        :param img1: 第一张图像
        :param img2: 第二张图像
        :return: 差异度，0表示完全相同，1表示完全不同
        """
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        gray1 = img1.convert("L")
        gray2 = img2.convert("L")

        diff = ImageChops.difference(gray1, gray2)
        diff_array = np.array(diff, dtype=np.float32)
        mean_diff = np.mean(diff_array)

        return float(mean_diff / 255.0)

    @staticmethod
    def is_significant_change(
        img1: Image.Image, img2: Image.Image, threshold: float = 0.05
    ) -> bool:
        """
        判断两张图像是否有显著变化

        :param img1: 第一张图像
        :param img2: 第二张图像
        :param threshold: 变化阈值（0~1），默认 5%
        :return: True 表示有显著变化
        """
        return ImageDiff.calculate_diff_ratio(img1, img2) >= threshold

    @staticmethod
    def quick_hash(image: Image.Image) -> int:
        """
        计算图像的快速感知哈希（用于快速排除相同画面）

        :param image: 输入图像
        :return: 64位感知哈希整数
        """
        small = image.resize((8, 8), Image.Resampling.LANCZOS).convert("L")
        pixels = np.array(small)
        avg = np.mean(pixels)
        hash_bits = (pixels > avg).flatten()
        hash_int = 0
        for i, bit in enumerate(hash_bits):
            if bit:
                hash_int |= 1 << i
        return hash_int


def wait_for_change(
    screenshot_provider: Callable,
    previous_screenshot: Image.Image,
    timeout: float = 5.0,
    threshold: float = 0.05,
    interval: float = 0.2,
) -> bool:
    """
    等待画面发生显著变化（替代固定 sleep）

    在 timeout 秒内以 interval 间隔轮询截图，
    一旦画面变化超过 threshold 则认为"画面已变"并返回。

    典型用途：
        prev = auto.screenshot.copy()
        auto.click_element("some_button_assets.png")
        wait_for_change(auto.take_screenshot, prev)

    :param screenshot_provider: 返回 PIL.Image 的可调用对象
    :param previous_screenshot: 变化前的参考截图
    :param timeout: 最大等待秒数
    :param threshold: 变化阈值
    :param interval: 轮询间隔秒数
    :return: True=检测到变化, False=超时
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = screenshot_provider()
        if current is None:
            time.sleep(interval)
            continue
        if ImageDiff.is_significant_change(previous_screenshot, current, threshold):
            return True
        time.sleep(interval)
    return False


def wait_for_stable(
    screenshot_provider: Callable,
    timeout: float = 5.0,
    stable_count: int = 3,
    threshold: float = 0.03,
    interval: float = 0.2,
) -> Optional[Image.Image]:
    """
    等待画面稳定（多次采样无明显变化后返回）

    适用于等待加载动画/过渡动画完全结束。

    :param screenshot_provider: 返回 PIL.Image 的可调用对象
    :param timeout: 最大等待秒数
    :param stable_count: 连续稳定帧数要求
    :param threshold: 变化阈值（比 wait_for_change 更严格）
    :param interval: 轮询间隔秒数
    :return: 稳定后的截图；超时返回 None
    """
    frames: list[Image.Image] = []
    deadline = time.time() + timeout

    while time.time() < deadline:
        current = screenshot_provider()
        if current is None:
            time.sleep(interval)
            continue

        frames.append(current)
        if len(frames) < 2:
            time.sleep(interval)
            continue

        # 只保留最近 stable_count + 1 帧
        if len(frames) > stable_count + 1:
            frames.pop(0)

        # 检查最近 stable_count 对差异是否都低于阈值
        recent = frames[-(stable_count + 1):]
        all_stable = True
        for i in range(len(recent) - 1):
            if ImageDiff.calculate_diff_ratio(recent[i], recent[i + 1]) >= threshold:
                all_stable = False
                break

        if all_stable:
            return current

        time.sleep(interval)

    return None
