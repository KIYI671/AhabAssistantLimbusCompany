import gc
import math
import random
import threading
import time
from ast import List
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import psutil
from PIL.Image import Image

from utils.image_utils import ImageUtils
from utils.path_manager import path_manager
from utils.singletonmeta import SingletonMeta

from ..config import cfg
from ..logger import log
from ..ocr import ocr
from .input_handlers.input import AbstractInput
from .screenshot import ScreenShot

_FRAME_CACHE_MISS = object()
# ponytail: 交互门最长关闭时间。监控线程卡在持久弹窗上时,超时放行业务输入,
# 恢复 retry() 等流程的卡死看门狗(kill_game/restart_game)。
GATE_WAIT_TIMEOUT = 30.0


@dataclass(frozen=True)
class TextMatchResult:
    """Structured result for dict-based OCR target matches."""

    value: Any
    text: str
    position: list[float]


class Automation(metaclass=SingletonMeta):
    """自动化管理类，用于管理与游戏窗口有关的自动化操作"""

    def __init__(self, windows_title):
        self.windows_title = windows_title
        self.screenshot = None
        self._frame_dirty = True
        self._last_target_action_time = {}
        self.input_handler = AbstractInput()
        self._screenshot_lock = threading.RLock()
        self._latest_screenshot = None
        self._latest_screenshot_monotonic = 0.0
        self._input_lock = threading.RLock()
        self._interaction_gate = threading.Event()
        self._interaction_gate.set()

        self.init_input()

        self.img_cache = {}
        self._screenshot_array = None
        self._screenshot_array_source = None
        self._frame_match_cache = {}
        self._frame_ocr_cache = {}
        self._last_memory_check_time = 0.0
        self.last_screenshot_time = 0
        self.last_click_time = 0
        self.model = "clam"

    def init_input(self):
        """初始化输入处理器，将输入操作如点击、拖动等绑定至实例变量"""
        if self.input_handler:
            self.input_handler = None
        if cfg.simulator:
            if cfg.simulator_type == 0:
                from .input_handlers.simulator.mumu_control import MumuControl

                log.debug("使用MuMu模拟器输入模块")
                if MumuControl.connection_device is not None:
                    self.input_handler = MumuControl.connection_device
            else:
                from .input_handlers.simulator.simulator_control import SimulatorControl

                log.debug("使用基于PyMiniTouch的通用模拟器输入模块")
                self.input_handler = SimulatorControl.connection_device
        else:
            input_type = cfg.win_input_type
            if input_type == "background":
                from .input_handlers.input import BackgroundInput

                log.debug("使用后台点击模块")
                self.input_handler = BackgroundInput()
            elif input_type == "foreground":
                from .input_handlers.input import Input

                log.debug("使用前台点击模块")
                self.input_handler = Input()
            elif input_type == "window_move":
                from .input_handlers.input import WindowMoveInput

                log.debug("使用基于窗口移动的后台点击模块")
                self.input_handler = WindowMoveInput()
        if self.input_handler is None:
            from .input_handlers.input import BackgroundInput

            self.input_handler = BackgroundInput()
        assert isinstance(self.input_handler, AbstractInput), "输入处理器必须是AbstractInput的实例"
        self.set_pause = self.input_handler.set_pause
        self.wait_pause = self.input_handler.wait_pause
        self.memory_protection = cfg.memory_protection

    def _mark_frame_dirty(self) -> None:
        """输入后同时失效业务帧和监控线程可复用的最近帧。"""
        self._frame_dirty = True
        screenshot_lock = getattr(self, "_screenshot_lock", None)
        if screenshot_lock is None:
            self._latest_screenshot_monotonic = 0.0
            return
        with screenshot_lock:
            self._latest_screenshot_monotonic = 0.0

    def can_reuse_current_frame(self, max_age: float = 0.5) -> bool:
        """当前截图存在、足够新，且截图后没有执行可能改变画面的输入动作。"""
        if self.screenshot is None or getattr(self, "_frame_dirty", True):
            return False
        last_screenshot = getattr(self, "last_screenshot_time", None)
        if last_screenshot is None:
            return True
        return time.monotonic() - last_screenshot <= max(0.0, float(max_age))

    def suspend_interactions(self) -> None:
        """暂时阻止业务线程继续点击。"""
        self._interaction_gate.clear()

    def resume_interactions(self) -> None:
        """恢复业务线程点击。"""
        self._interaction_gate.set()

    def reset_safety_locks(self) -> None:
        """线程被强制终止后换新锁,清除可能残留的持有状态。

        仅应在 my_script_task.terminate() 等硬杀路径调用:被杀线程持有的
        RLock 计数不会释放,不换锁则后续任务取锁永久阻塞。
        """
        self._input_lock = threading.RLock()
        self._screenshot_lock = threading.RLock()

    def _run_input_and_mark_frame_dirty(self, method_name: str, *args, **kwargs):
        method = getattr(self.input_handler, method_name)
        result = method(*args, **kwargs)
        if result is not False:
            self._mark_frame_dirty()
        return result

    def _run_business_interaction(self, method_name: str, *args, **kwargs):
        """在交互门放行且取得输入锁后执行一次业务输入。

        交互门可能在等待输入锁期间被监控线程关闭，因此取得锁后需要再次确认。
        门连续关闭超过 GATE_WAIT_TIMEOUT 时视为监控卡在持久弹窗上，放行业务
        输入，让业务流程自身的卡死兜底(如 check_times)得以继续运行。
        """
        while True:
            gate_open = self._interaction_gate.wait(timeout=GATE_WAIT_TIMEOUT)
            with self._input_lock:
                if gate_open and not self._interaction_gate.is_set():
                    # 等待输入锁期间门被关闭：重新等待。
                    continue
                return self._run_input_and_mark_frame_dirty(method_name, *args, **kwargs)

    def mouse_click(self, x, y, times=1):
        return self._run_business_interaction("mouse_click", x, y, times=times)

    def mouse_click_blank(self, *args, **kwargs):
        return self._run_business_interaction("mouse_click_blank", *args, **kwargs)

    def mouse_drag(self, *args, **kwargs):
        return self._run_business_interaction("mouse_drag", *args, **kwargs)

    def mouse_swipe_for_scroll(self, *args, **kwargs):
        return self._run_business_interaction("mouse_swipe_for_scroll", *args, **kwargs)

    def mouse_drag_down(self, *args, **kwargs):
        return self._run_business_interaction("mouse_drag_down", *args, **kwargs)

    def mouse_scroll(self, *args, **kwargs):
        return self._run_business_interaction("mouse_scroll", *args, **kwargs)

    def mouse_to_blank(self, *args, **kwargs):
        return self._run_business_interaction("mouse_to_blank", *args, **kwargs)

    def mouse_drag_link(self, *args, **kwargs):
        return self._run_business_interaction("mouse_drag_link", *args, **kwargs)

    def key_press(self, *args, **kwargs):
        return self._run_business_interaction("key_press", *args, **kwargs)

    def input_text(self, *args, **kwargs):
        return self._run_business_interaction("input_text", *args, **kwargs)

    def monitor_mouse_click(self, x, y, times=1):
        """由系统监控线程点击，不等待该监控线程设置的互斥门。"""
        with self._input_lock:
            return self._run_input_and_mark_frame_dirty("mouse_click", x, y, times=times)

    def _remember_screenshot(self, screenshot: Image | None) -> None:
        if screenshot is None:
            return
        self._latest_screenshot = screenshot
        self._latest_screenshot_monotonic = time.monotonic()

    def invalidate_screenshot_cache(self) -> None:
        """让业务线程与监控线程在下一轮检查时都获取新截图。"""
        self._mark_frame_dirty()

    def take_monitor_screenshot(self, gray: bool = True, max_age: float = 0.0) -> Image | None:
        """获取监控截图，优先复用业务线程的最近帧且不覆盖业务截图。"""
        with self._input_lock, self._screenshot_lock:
            if (
                self._latest_screenshot is not None
                and max_age > 0
                and time.monotonic() - self._latest_screenshot_monotonic <= max_age
            ):
                if gray and self._latest_screenshot.mode != "L":
                    return self._latest_screenshot.convert("L")
                return self._latest_screenshot

            screenshot = ScreenShot.take_screenshot(gray)
            self._remember_screenshot(screenshot)
            return screenshot

    def check_pause(self) -> bool:
        """
        检查是否处于暂停状态

        Returns:
            bool: 是否处于暂停状态
        """
        return self.input_handler.is_pause

    def get_restore_time(self) -> float:
        """
        获取上一次结束暂停的时间
        Returns:
            float: 上一次结束暂停的时间
        """
        return self.input_handler.restore_time if self.input_handler.restore_time else 0

    def click_element(
        self,
        target,
        find_type="image",
        threshold=0.8,
        max_retries=1,
        take_screenshot=False,
        offset=True,
        action="click",
        times=1,
        dx=0,
        dy=0,
        model=None,
        my_crop=None,
        click=True,
        drag_time=None,
        interval=0.5,
    ):
        """查找并点击屏幕上的元素。

        ``interval`` 是同一目标的独立冷却；不同目标只受全局物理输入间隔限制。
        """
        if model is None:
            model = self.model
        coordinates = self.find_element(
            target,
            find_type,
            threshold,
            max_retries,
            take_screenshot,
            model=model,
            my_crop=my_crop,
            additional_stack=1,
        )
        if coordinates:
            if click:
                cooldown_key = self._click_cooldown_key(target, find_type, action)
                if self._target_action_is_cooling_down(cooldown_key, interval):
                    return False
                result = self.mouse_action_with_pos(
                    coordinates,
                    offset,
                    action,
                    times,
                    drag_time,
                    dx,
                    dy,
                    find_type,
                    None,
                )
                if result:
                    self._record_target_action(cooldown_key)
                return result
            return coordinates
        return False

    @classmethod
    def _freeze_click_target(cls, target):
        if isinstance(target, dict):
            return tuple(sorted((str(key), cls._freeze_click_target(value)) for key, value in target.items()))
        if isinstance(target, (list, tuple)):
            return tuple(cls._freeze_click_target(value) for value in target)
        try:
            hash(target)
        except TypeError:
            return repr(target)
        return target

    @classmethod
    def _click_cooldown_key(cls, target, find_type, action):
        return find_type, action, cls._freeze_click_target(target)

    def _target_action_is_cooling_down(self, key, cooldown) -> bool:
        cooldown = max(0.0, float(cooldown or 0.0))
        if cooldown == 0:
            return False
        last_action = getattr(self, "_last_target_action_time", {}).get(key)
        return last_action is not None and time.monotonic() - last_action < cooldown

    def _record_target_action(self, key) -> None:
        actions = getattr(self, "_last_target_action_time", None)
        if actions is None:
            actions = self._last_target_action_time = {}
        now = time.monotonic()
        actions[key] = now
        if len(actions) > 512:
            cutoff = now - 60
            actions = {target: timestamp for target, timestamp in actions.items() if timestamp > cutoff}
            if len(actions) > 512:
                actions = dict(sorted(actions.items(), key=lambda item: item[1], reverse=True)[:256])
            self._last_target_action_time = actions

    def calculate_click_position(self, coordinates, offset=True):
        """
        根据给定的坐标计算点击位置。
        参数:
        coordinates (tuple): 一个包含(x, y)坐标的元组，表示点击的位置。
        返回:
        tuple: 经过计算后的点击位置坐标。
        """
        # TODO:后续适配无需窗口设置模式
        x, y = coordinates
        screenshot = self.get_screenshot_array()
        if offset:
            x = max(0, min(screenshot.shape[1], x + random.randint(-10, 10)))
            y = max(0, min(screenshot.shape[0], y + random.randint(-10, 10)))
        return x, y

    def mouse_action_with_pos(
        self,
        coordinates,
        offset=True,
        action="click",
        times=1,
        drag_time=None,
        dx=0,
        dy=0,
        find_type=None,
        interval=None,
    ) -> bool:
        """
        在指定坐标上执行点击操作
        Args:
            coordinates: 坐标位置，用于计算点击位置
            offset: 是否使用偏移量计算点击位置，默认为True
            action: 鼠标操作类型，默认为"click"
            move_back: 是否在操作后将鼠标移动回原位置，默认为False
        Returns:
           bool (True) : 总是返回True表示操作执行完毕
        """
        if find_type == "image_with_multiple_targets" and len(coordinates) > 0:
            for c in coordinates:
                self.mouse_action_with_pos(
                    c,
                    offset=offset,
                    action=action,
                    times=times,
                    drag_time=drag_time,
                    dx=dx,
                    dy=dy,
                    find_type="image",
                    interval=1,
                )
            return True

        if interval is None:
            interval = max(0.0, float(cfg.mouse_action_interval or 0.0))
        else:
            interval = max(0.0, float(interval))

        if self.last_click_time:
            elapsed = time.monotonic() - self.last_click_time
            remaining = interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

        # 计算传入的位置
        self._interaction_gate.wait(timeout=GATE_WAIT_TIMEOUT)
        x, y = self.calculate_click_position(coordinates, offset)

        # 定义鼠标操作映射
        action_map = {
            "click": self.mouse_click,
            "drag": self.mouse_drag,
            "drag_down": self.mouse_drag_down,
            "scroll": self.mouse_scroll,
        }
        # 根据操作类型执行相应的鼠标操作
        if action in action_map:
            if action == "click":
                self.mouse_click(x, y, times=times)
            elif action == "drag":
                self.mouse_drag(x, y, drag_time=drag_time, dx=dx, dy=dy)
            elif action == "drag_down":
                self.mouse_drag_down(x, y)
            elif action == "scroll":
                self.mouse_scroll()
            self.last_click_time = time.monotonic()
        else:
            # 如果操作类型未知，抛出异常
            raise ValueError(f"未知的操作类型{action}")

        return True

    def take_screenshot(self, gray: bool = True, interval: float | None = None) -> Image | None:
        """
        截取当前屏幕并返回图像对象。
        Args:
            gray (bool): 是否将图像转换为灰度图，默认为True。
            interval (float | None): 仅覆盖本次截图的最小间隔；默认使用全局配置。
        Returns:
            Image: 截取当前屏幕的图像对象
        """
        start_time = time.monotonic()
        configured_interval = cfg.screenshot_interval if cfg.screenshot_interval else 0.15
        screenshot_interval_time = configured_interval if interval is None else max(0.0, float(interval))
        while True:
            try:
                elapsed = time.monotonic() - self.last_screenshot_time
                if elapsed < screenshot_interval_time:
                    time.sleep(screenshot_interval_time - elapsed)

                # 与输入使用相同的加锁顺序，避免截图完成后、提交干净帧前被监控线程点击。
                with self._input_lock, self._screenshot_lock:
                    result = ScreenShot.take_screenshot(gray)
                    self._remember_screenshot(result)
                    if result:
                        self.screenshot = result
                        self._reset_frame_cache(result)
                        self._frame_dirty = False
                        self.last_screenshot_time = time.monotonic()
                        return result
                    return None
            except Exception as e:
                log.error(f"截图失败:{e}")
            time.sleep(1)
            if time.monotonic() - start_time > 60:
                log.error("截图超时，尝试重启游戏")
                import os

                import win32process

                from module.game_and_screen import screen

                try:
                    _, pid = win32process.GetWindowThreadProcessId(screen.handle.hwnd)
                    os.system(f"taskkill /F /PID {pid}")
                except:
                    pass
                from tasks.base.script_task_scheme import init_game

                init_game()
                start_time = time.monotonic()

    def _reset_frame_cache(self, screenshot=None) -> None:
        """在截图变化时清除只对当前帧有效的派生数据。"""
        if screenshot is None:
            screenshot = self.screenshot
        self._screenshot_array_source = screenshot
        self._screenshot_array = None
        self._frame_match_cache = {}
        self._frame_ocr_cache = {}

    def _ensure_frame_cache_current(self) -> None:
        """兼容少数直接替换 auto.screenshot 的调用点。"""
        if getattr(self, "_screenshot_array_source", None) is not self.screenshot:
            self._reset_frame_cache(self.screenshot)

    def get_screenshot_array(self):
        """返回当前截图的共享 NumPy 视图，避免每次匹配复制整张图。"""
        self._ensure_frame_cache_current()
        if self.screenshot is None:
            return None
        if self._screenshot_array is None:
            self._screenshot_array = np.asarray(self.screenshot)
        return self._screenshot_array

    def get_region_sample(self, crop, max_edge: int = 320) -> np.ndarray | None:
        """从当前帧提取小尺寸灰度区域，用于轻量级稳定性判断。"""
        screenshot = self.get_screenshot_array()
        if screenshot is None:
            return None

        region = ImageUtils.crop(screenshot, crop, copy=False)
        if region.size == 0:
            return None
        if region.ndim == 3:
            if region.shape[2] == 4:
                region = cv2.cvtColor(region, cv2.COLOR_RGBA2GRAY)
            else:
                region = cv2.cvtColor(region[:, :, :3], cv2.COLOR_RGB2GRAY)
        elif region.ndim != 2:
            return None

        height, width = region.shape[:2]
        if height <= 0 or width <= 0:
            return None
        if max_edge > 0 and max(height, width) > max_edge:
            scale = max_edge / max(height, width)
            region = cv2.resize(
                region,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        return np.ascontiguousarray(region).copy()

    def wait_until_region_stable(
        self,
        crop,
        *,
        timeout: float = 3.0,
        poll_interval: float = 0.25,
        stable_samples: int = 2,
        pixel_delta_threshold: int = 12,
        max_changed_ratio: float = 0.02,
        initial_sample: np.ndarray | None = None,
        require_change: bool = False,
    ) -> bool:
        """等待局部区域连续稳定，避免用固定 sleep 等待界面刷新。"""
        if stable_samples < 1:
            raise ValueError("stable_samples must be at least 1")
        if not 0 <= max_changed_ratio <= 1:
            raise ValueError("max_changed_ratio must be between 0 and 1")

        deadline = time.monotonic() + max(0.0, timeout)
        previous = None if initial_sample is None else np.ascontiguousarray(initial_sample).copy()
        change_seen = not require_change
        consecutive_stable = 0

        while time.monotonic() < deadline:
            if self.take_screenshot(interval=poll_interval) is None:
                continue
            current = self.get_region_sample(crop)
            if current is None:
                continue

            if previous is not None:
                if current.shape != previous.shape:
                    changed_ratio = 1.0
                else:
                    difference = cv2.absdiff(current, previous)
                    changed_ratio = float(np.count_nonzero(difference >= pixel_delta_threshold)) / difference.size

                if changed_ratio <= max_changed_ratio:
                    if change_seen:
                        consecutive_stable += 1
                        if consecutive_stable >= stable_samples:
                            return True
                else:
                    change_seen = True
                    consecutive_stable = 0

            previous = current

        return False

    def wait_for_element(
        self,
        target,
        *,
        timeout: float = 2.0,
        poll_interval: float = 0.15,
        click: bool = False,
        find_type: str = "image",
        threshold: float = 0.8,
        model=None,
        my_crop=None,
        offset=True,
        action="click",
        times=1,
        interval=0.5,
    ):
        """在连续新帧上等待目标，出现即返回或点击，不固定睡满动画时长。"""
        deadline = time.monotonic() + max(0.0, float(timeout))
        reuse_current = self.can_reuse_current_frame()

        while time.monotonic() < deadline:
            if reuse_current:
                reuse_current = False
            elif self.take_screenshot(interval=poll_interval) is None:
                continue

            position = self.find_element(
                target,
                find_type=find_type,
                threshold=threshold,
                model=model,
                my_crop=my_crop,
            )
            if not position:
                continue
            if not click:
                return position
            if self.click_element(
                target,
                find_type=find_type,
                threshold=threshold,
                model=model,
                my_crop=my_crop,
                offset=offset,
                action=action,
                times=times,
                interval=interval,
            ):
                return True

        return False

    @staticmethod
    def _normalize_crop_for_cache(crop):
        if crop is None:
            return None
        return tuple(round(float(value), 4) for value in crop)

    def find_element(
        self,
        target,
        find_type="image",
        threshold=0.8,
        max_retries=1,
        take_screenshot=False,
        model=None,
        my_crop=None,
        min_dist=10,
        additional_stack=0,
    ):
        """
        查找元素，并根据指定的查找类型执行不同的查找策略。
        Args:
            target: 查找目标，可以是图像路径或文字。(zh_cn)->en->share
            find_type: 查找类型，例如'image', 'text'等。
            threshold: 查找阈值，用于图像查找时的相似度匹配。
            max_retries: 最大重试次数。
            take_screenshot: 是否需要先截图。
            model: 查找的策略,'clam' 为在模板图片位置查找，'normal' 为模板图片位置扩大范围查找，'aggressive' 为全截屏区域查找
            my_crop: 用于限制图像或OCR识别范围的裁剪区域
            min_dist: 多目标图像查找时的NMS最小距离。
            additional_stack: 用于日志堆栈层级调整
        Returns:
            查找到的元素位置，或者在图像计数查找时返回计数。
        """
        if model is None:
            model = self.model
        # 如果不需要截图，则重试次数设置为1
        max_retries = 1 if not take_screenshot else max_retries
        for i in range(max_retries):
            if take_screenshot:
                # 截图并根据裁剪参数获取截图结果
                while self.take_screenshot() is None:
                    continue
            # 根据查找类型执行不同的查找策略
            if find_type in ["image", "text"]:
                center = None
                if find_type in ["image"]:
                    # 使用图像查找方法查找元素
                    center = self.find_image_element(
                        target,
                        threshold,
                        model=model,
                        my_crop=my_crop,
                        additional_stack=additional_stack,
                    )
                elif find_type == "text":
                    # 使用文本查找方法查找元素
                    center = self.find_text_element(target, my_crop, additional_stack=additional_stack)
                if center:
                    return center
            elif find_type in ["feature"]:
                return self.find_feature_element(target, my_crop, additional_stack=additional_stack)
            elif find_type in ["image_with_multiple_targets"]:
                # 使用多目标图像查找方法查找元素
                return self.find_image_with_multiple_targets(
                    target, threshold, my_crop=my_crop, min_dist=min_dist, additional_stack=additional_stack
                )
            else:
                raise ValueError("错误的类型")

            if i < max_retries - 1:
                time.sleep(1)  # 在重试前等待一定时间
        return None

    def find_image_with_multiple_targets(self, target: str, threshold, my_crop=None, min_dist=10, additional_stack=0) -> List:
        """
        在当前截图中查找多个目标图像的位置
        """
        try:
            self._ensure_frame_cache_current()
            cache_key = (
                "image_multiple",
                target,
                float(threshold),
                self._normalize_crop_for_cache(my_crop),
                float(min_dist),
                path_manager.current_theme,
                path_manager.current_language,
                tuple(path_manager.pic_path),
            )
            cached = self._frame_match_cache.get(cache_key, _FRAME_CACHE_MISS)
            if cached is not _FRAME_CACHE_MISS:
                return list(cached)

            existing_paths = ImageUtils.existing_image_paths(target)
            if not existing_paths:
                log.error(f"未找到图片： {target} ")
                self._frame_match_cache[cache_key] = ()
                return []
            template, _ = self._load_template_for_path(target, existing_paths[0], cacheable=True)
            if template is None:
                raise ValueError("读取图片失败")
            screenshot = self.get_screenshot_array()
            crop_offset = (0, 0)
            if my_crop:
                crop_offset = (int(round(my_crop[0])), int(round(my_crop[1])))
                screenshot = ImageUtils.crop(screenshot, my_crop)
            matches = ImageUtils.match_template_with_multiple_targets(screenshot, template, threshold, min_dist=min_dist)
            if crop_offset != (0, 0):
                matches = [(x + crop_offset[0], y + crop_offset[1]) for x, y in matches]
            if len(matches) == 0:
                log.debug(f"未找到任何目标图像{target}", stacklevel=additional_stack + 3)
                self._frame_match_cache[cache_key] = ()
                return []
            else:
                log.debug(
                    f"找到{len(matches)}个目标：{matches}",
                    stacklevel=additional_stack + 3,
                )
                self._frame_match_cache[cache_key] = tuple(matches)
                return matches
        except Exception as e:
            log.error(f"寻找图片出错:{e}")
            return []

    def find_str_in_text(self, target, ocr_dict):
        """
        返回目标文本的坐标
        """
        for text in ocr_dict.keys():
            if target.lower() in text.lower():
                log.debug(f"识别到目标：{text},坐标为：{ocr_dict[text]}")
                return ocr_dict[text]
            # 去除空格后再匹配，解决OCR识别结果带空格的问题（如 "HongLu" vs "Hong Lu"）
            if target.replace(" ", "").lower() in text.replace(" ", "").lower():
                log.debug(f"识别到目标（去空格匹配）：{text},坐标为：{ocr_dict[text]}")
                return ocr_dict[text]
        return False

    def _get_cached_ocr_result(self, my_crop=None):
        """同一帧、同一裁剪区域的 OCR 结果只计算一次。"""
        self._ensure_frame_cache_current()
        cache_key = ("ocr", self._normalize_crop_for_cache(my_crop))
        cached = self._frame_ocr_cache.get(cache_key, _FRAME_CACHE_MISS)
        if cached is not _FRAME_CACHE_MISS:
            return cached
        if my_crop is not None:
            cropped_image = self.screenshot.crop(my_crop)
            ocr_result = ocr.run(cropped_image)
        else:
            ocr_result = ocr.run(self.screenshot)
        self._frame_ocr_cache[cache_key] = ocr_result
        return ocr_result

    def _run_ocr_for_text(self, my_crop=None, only_text=False, additional_stack=0):
        ocr_result = self._get_cached_ocr_result(my_crop)

        if not ocr_result.txts:
            return False if only_text else {}

        ocr_text_list = [ocr_result.txts[i] for i in range(len(ocr_result.txts))]
        if only_text:
            return ocr_text_list

        ocr_position_list = []
        for box in ocr_result.boxes:
            x = (box[0][0] + box[2][0]) / 2
            y = (box[0][1] + box[2][1]) / 2
            ocr_position_list.append([x, y])

        ocr_dict = {text: position for text, position in zip(ocr_text_list, ocr_position_list)}
        log.debug(f"识别到文本及其坐标：{ocr_dict}", stacklevel=additional_stack + 3)
        return ocr_dict

    def _find_target_in_ocr_dict(self, target, ocr_dict, all_text=False):
        if ocr_dict == {}:
            return False
        if isinstance(target, str):
            return self.find_str_in_text(target, ocr_dict)
        elif isinstance(target, list):
            if all_text:
                for key in target:
                    if self.find_str_in_text(str(key), ocr_dict) is False:
                        return False
                return True
            for key in target:
                if result := self.find_str_in_text(str(key), ocr_dict):
                    return result
            return False
        elif isinstance(target, dict):
            for key, value in target.items():
                if position := self.find_str_in_text(str(key), ocr_dict):
                    return TextMatchResult(value=value, text=str(key), position=position)
            return None
        return False

    def find_language_text(
        self,
        zh_text,
        en_text,
        my_crop=None,
        all_text=False,
        additional_stack=0,
    ):
        """
        按当前语言状态查找中英文文本，并在语言未知时用命中结果同步语言。

        该方法只执行一次 OCR，然后在同一份 OCR 结果中匹配文本：
        - 当前语言为 zh_cn 时，只匹配 zh_text。
        - 当前语言为 en 时，只匹配 en_text。
        - 当前语言未知时，先匹配 zh_text；中文命中则同步语言为 zh_cn。
        - 中文未命中时再匹配 en_text；英文命中则同步语言为 en，并移除 zh_cn 图片路径。

        Args:
            zh_text: 中文目标文本，支持 str、list、dict，规则同 find_text_element。
            en_text: 英文目标文本，支持 str、list、dict，规则同 find_text_element。
            my_crop: OCR 裁剪区域，格式为 (x1, y1, x2, y2)；为 None 时识别整张截图。
            all_text: 当目标文本为 list 时，是否要求列表内所有关键词全部命中。
            additional_stack: 日志 stacklevel 补偿，用于让日志定位到业务调用处。

        Returns:
            文本命中结果，返回格式同 find_text_element；未命中返回 False。
        """
        ocr_dict = self._run_ocr_for_text(my_crop=my_crop, additional_stack=additional_stack)
        if ocr_dict == {}:
            return False

        if path_manager.current_language == "zh_cn":
            return self._find_target_in_ocr_dict(zh_text, ocr_dict, all_text=all_text)
        if path_manager.current_language == "en":
            return self._find_target_in_ocr_dict(en_text, ocr_dict, all_text=all_text)

        zh_result = self._find_target_in_ocr_dict(zh_text, ocr_dict, all_text=all_text)
        if zh_result is not False and zh_result is not None:
            path_manager.set_language("zh_cn", log_stacklevel=additional_stack + 4)
            return zh_result

        en_result = self._find_target_in_ocr_dict(en_text, ocr_dict, all_text=all_text)
        if en_result is not False and en_result is not None:
            path_manager.set_language("en", log_stacklevel=additional_stack + 4)
            if path_manager.eliminate_zh_cn_paths():
                self.clear_img_cache()
            return en_result

        return False

    def find_text_element(self, target, my_crop=None, all_text=False, only_text=False, additional_stack=0):
        """
        寻找文本元素所在的坐标位置。

        str/list 目标返回坐标；dict 目标返回 TextMatchResult。
        """
        ocr_result = self._run_ocr_for_text(my_crop=my_crop, only_text=only_text, additional_stack=additional_stack)
        if only_text:
            return ocr_result
        return self._find_target_in_ocr_dict(target, ocr_result, all_text=all_text)

    def get_text_from_screenshot(self, my_crop=None):
        """
        从屏幕截图中提取文字
        """
        ocr_result = self._get_cached_ocr_result(my_crop)
        if ocr_result.txts:
            ocr_text_list = [ocr_result.txts[i] for i in range(len(ocr_result.txts))]
        else:
            ocr_text_list = []

        return ocr_text_list

    def _prepare_feature_target(self, pic_crop=None):
        """将目标区域统一到 1440p 模板坐标，并只提取一次特征。"""
        normalize_scale = 1440 / cfg.set_win_size

        if pic_crop:
            # 节点区域通常只占屏幕约 1%，先裁剪可避免每个候选节点都缩放整张 4K 截图。
            screenshot = ImageUtils.crop(self.get_screenshot_array(), pic_crop)
            if not math.isclose(normalize_scale, 1.0):
                normalized_crop = [int(i * normalize_scale) for i in pic_crop]
                target_width = max(1, normalized_crop[2] - normalized_crop[0])
                target_height = max(1, normalized_crop[3] - normalized_crop[1])
                screenshot = cv2.resize(
                    screenshot,
                    (target_width, target_height),
                    interpolation=cv2.INTER_AREA,
                )
            return ImageUtils.extract_orb_features(screenshot)

        screenshot = self.get_screenshot_array()
        if not math.isclose(normalize_scale, 1.0):
            screenshot = cv2.resize(
                screenshot,
                None,
                fx=normalize_scale,
                fy=normalize_scale,
                interpolation=cv2.INTER_AREA,
            )
        return ImageUtils.extract_orb_features(screenshot)

    def _load_cached_feature_template(self, target: str):
        """按当前主题/语言缓存模板 ORB 特征；图片缓存刷新时会一并失效。"""
        existing_paths = ImageUtils.existing_image_paths(target)
        if not existing_paths:
            return None
        target_path = existing_paths[0]
        cache_key = ("orb_feature", target, target_path)
        cached = self.img_cache.get(cache_key)
        if cached is not None:
            return cached

        template = ImageUtils.load_from_specific_path(target, target_path, resize=False)
        if template is None:
            return None
        features = ImageUtils.extract_orb_features(template)
        self.img_cache[cache_key] = features
        return features

    def find_first_feature_element(self, targets, pic_crop=None, additional_stack=0):
        """按顺序匹配多个特征模板，并复用同一份截图特征。"""
        try:
            target_features = self._prepare_feature_target(pic_crop)
            for target, min_matches in targets:
                template_features = self._load_cached_feature_template(target)
                if template_features is None:
                    continue
                result, num_matches = ImageUtils.match_orb_features(
                    template_features,
                    target_features,
                    min_matches,
                )
                log.debug(
                    f"匹配目标特征图片：{target.replace('./assets/images/', '')}结果{result}, "
                    f"找到 {num_matches} 个匹配点",
                    stacklevel=additional_stack + 3,
                )
                if result:
                    return target
        except Exception as e:
            if "cv::flann" not in str(e):
                log.error(f"匹配图片特征失败:{e}")
        return None

    def find_feature_element(self, target, pic_crop=None, min_matches=8, additional_stack=0):
        """寻找单个特征元素；内部复用批量匹配实现。"""
        return self.find_first_feature_element(
            [(target, min_matches)],
            pic_crop=pic_crop,
            additional_stack=additional_stack + 1,
        ) is not None

    def clear_img_cache(self) -> None:
        """清除图片缓存"""
        self.img_cache.clear()
        getattr(self, "_frame_match_cache", {}).clear()
        gc.collect()  # 强制垃圾回收，清理内存
        log.debug("图片缓存已清除", stacklevel=2)

    def _load_template_for_path(self, target: str, target_path: str, cacheable: bool):
        cache_key = (target, target_path)
        if cacheable and cache_key in self.img_cache:
            cached = self.img_cache[cache_key]
            return cached["template"], cached["bbox"]

        template = ImageUtils.load_from_specific_path(target, target_path)
        if template is None:
            return None, None
        if target.endswith("assets.png"):
            bbox = ImageUtils.get_bbox(template)
            template = ImageUtils.crop(template, bbox)
        else:
            bbox = None
        if cacheable:
            self.img_cache[cache_key] = {"template": template, "bbox": bbox}
        return template, bbox

    @staticmethod
    def _is_valid_match(match_val, threshold) -> bool:
        return (
            isinstance(match_val, (int, float, np.integer, np.floating))
            and not math.isinf(match_val)
            and match_val >= threshold
        )

    MATCH_GAP = 0.15

    def _update_path_state_from_match_results(self, results, additional_stack: int = 0) -> None:
        dark_results = [result for result in results if path_manager.is_path_dark(result["path"])]
        default_results = [result for result in results if path_manager.is_path_default(result["path"])]
        zh_cn_results = [result for result in results if path_manager.is_path_zh_cn(result["path"])]
        en_results = [result for result in results if result["path"].endswith("/en")]
        share_results = [result for result in results if result["path"].endswith("/share")]

        dark_matched = any(result["matched"] for result in dark_results)
        default_matched = any(result["matched"] for result in default_results)

        path_changed = False
        if dark_matched and not default_matched:
            path_manager.set_theme("dark", log_stacklevel=additional_stack + 4)
        elif default_matched and dark_results and not dark_matched:
            path_manager.set_theme("default", log_stacklevel=additional_stack + 4)
            path_changed = path_manager.eliminate_dark_paths() or path_changed
        elif dark_matched and default_matched:
            best_dark = max(r["matchVal"] for r in dark_results if r["matched"])
            best_default = max(r["matchVal"] for r in default_results if r["matched"])
            if best_default - best_dark > self.MATCH_GAP:
                path_manager.set_theme("default", log_stacklevel=additional_stack + 4)
                path_changed = path_manager.eliminate_dark_paths() or path_changed
            elif best_dark - best_default > self.MATCH_GAP:
                path_manager.set_theme("dark", log_stacklevel=additional_stack + 4)

        zh_cn_matched = any(result["matched"] for result in zh_cn_results)
        en_matched = any(result["matched"] for result in en_results)
        share_matched = any(result["matched"] for result in share_results)

        # share 路径是语言无关资源，不能单独决定语言为英文
        if zh_cn_matched and not en_matched:
            path_manager.set_language("zh_cn", log_stacklevel=additional_stack + 4)
        elif en_matched and not zh_cn_matched:
            path_manager.set_language("en", log_stacklevel=additional_stack + 4)
            path_changed = path_manager.eliminate_zh_cn_paths() or path_changed
        elif zh_cn_matched and en_matched:
            best_zh = max(r["matchVal"] for r in zh_cn_results if r["matched"])
            best_en = max(r["matchVal"] for r in en_results if r["matched"])
            if best_en - best_zh > self.MATCH_GAP:
                path_manager.set_language("en", log_stacklevel=additional_stack + 4)
                path_changed = path_manager.eliminate_zh_cn_paths() or path_changed
            elif best_zh - best_en > self.MATCH_GAP:
                path_manager.set_language("zh_cn", log_stacklevel=additional_stack + 4)
        elif share_matched:
            # 仅命中 share 时保持当前语言未知/不变，等待后续专属语言资源判定
            pass

        if path_changed:
            self.clear_img_cache()

    @staticmethod
    def _path_state_is_known() -> bool:
        return path_manager.current_theme is not None and path_manager.current_language is not None

    MEMORY_CHECK_INTERVAL = 5.0

    def _check_memory_pressure(self) -> None:
        """内存保护无需在每次模板匹配时都查询系统状态。"""
        if not getattr(self, "memory_protection", False):
            return
        now = time.monotonic()
        last_check = getattr(self, "_last_memory_check_time", 0.0)
        if now - last_check < self.MEMORY_CHECK_INTERVAL:
            return
        self._last_memory_check_time = now
        current_percent = psutil.virtual_memory().percent
        if current_percent > 90:
            log.debug(f"当前系统内存总占用率: {current_percent}%，释放图片缓存")
            self.clear_img_cache()

    def _image_match_cache_key(self, target, threshold, model, my_crop):
        return (
            "image",
            target,
            float(threshold),
            model,
            self._normalize_crop_for_cache(my_crop),
            path_manager.current_theme,
            path_manager.current_language,
            tuple(path_manager.pic_path),
        )

    def find_image_element(
        self,
        target: str,
        threshold,
        cacheable=True,
        model="clam",
        my_crop=None,
        additional_stack=0,
    ):
        """
        在当前截图中查找目标图像的位置
        """
        try:
            self._ensure_frame_cache_current()
            cache_key = None
            if cacheable and self._path_state_is_known():
                cache_key = self._image_match_cache_key(target, threshold, model, my_crop)
                cached = self._frame_match_cache.get(cache_key, _FRAME_CACHE_MISS)
                if cached is not _FRAME_CACHE_MISS:
                    return cached

            self._check_memory_pressure()

            existing_paths = ImageUtils.existing_image_paths(target)
            if not existing_paths:
                log.error(f"未找到图片： {target} ")
                log.debug(f"无法加载图片: {target}", stacklevel=additional_stack + 3)
                if cache_key is not None:
                    self._frame_match_cache[cache_key] = None
                return None

            screenshot = self.get_screenshot_array()
            if my_crop:
                screenshot = ImageUtils.crop(screenshot, my_crop)

            results = []
            for loaded_path in existing_paths:
                template, bbox = self._load_template_for_path(target, loaded_path, cacheable)
                if template is None:
                    continue
                center, matchVal = ImageUtils.match_template(screenshot, template, bbox, model)
                matched = self._is_valid_match(matchVal, threshold)
                if 0.70 < matchVal < 0.90 and int(matchVal * 1000 + 1e-9) % 10 >= 5:
                    match_fmt = ".3f"
                else:
                    match_fmt = ".2f"
                log.debug(
                    f"目标图片：{target.replace('./assets/images/', '')}, 路径: {loaded_path}, 相似度：{matchVal:{match_fmt}}, 目标位置：{center}",
                    stacklevel=additional_stack + 3,
                )
                results.append(
                    {
                        "path": loaded_path,
                        "center": center,
                        "matched": matched,
                        "matchVal": matchVal,
                    }
                )
                if matched and self._path_state_is_known():
                    if cache_key is None:
                        cache_key = self._image_match_cache_key(target, threshold, model, my_crop)
                    self._frame_match_cache[cache_key] = center
                    return center

            if not results:
                log.debug(f"无法加载图片: {target}", stacklevel=additional_stack + 3)
                if cache_key is not None:
                    self._frame_match_cache[cache_key] = None
                return None

            self._update_path_state_from_match_results(results, additional_stack=additional_stack)
            matched_center = None
            for result in results:
                if result["matched"]:
                    matched_center = result["center"]
                    break
            if cacheable and self._path_state_is_known():
                cache_key = self._image_match_cache_key(target, threshold, model, my_crop)
                self._frame_match_cache[cache_key] = matched_center
            return matched_center
        except Exception as e:
            log.error(f"寻找图片失败:{e}")
        return None

    def get_screenshot_crop(self, crop):
        """
        获取指定区域的彩色截图
        """
        self.take_screenshot(False)
        screenshot = self.get_screenshot_array()
        screenshot = screenshot[:, :, ::-1]
        screenshot = ImageUtils.crop(screenshot, crop)
        return screenshot
