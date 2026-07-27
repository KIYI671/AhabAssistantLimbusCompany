import threading
import time

import cv2
import numpy as np

from module.automation import auto
from module.logger import log
from utils.image_utils import ImageUtils


class RetryMonitor:
    """独立处理服务器重试弹窗，避免业务流程各自重复实现。"""

    RETRY_TEMPLATE = "base/retry.png"
    TEMPLATE_PATHS = ("default/en", "default/zh_cn")

    def __init__(self, poll_interval: float = 0.5, click_cooldown: float = 2.0):
        self.poll_interval = poll_interval
        self.click_cooldown = click_cooldown
        self._stop_event = threading.Event()
        self._lifecycle_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._templates: tuple[np.ndarray, ...] = ()
        self._last_click_time = 0.0
        self._handling_retry = False
        self._clear_frames = 0

    def start(self) -> None:
        """加载模板并启动监控线程；重复调用不会创建多个线程。"""
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._templates = self._load_templates()
            if not self._templates:
                log.warning("未能加载通用重试按钮模板，重试监控线程未启动")
                return
            self._last_click_time = 0.0
            self._handling_retry = False
            self._clear_frames = 0
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="ServerRetryMonitor",
                daemon=True,
            )
            self._thread.start()
            log.debug("通用服务器重试监控线程已启动")

    def stop(self) -> None:
        """停止监控并确保业务点击门恢复。"""
        with self._lifecycle_lock:
            thread = self._thread
            self._thread = None
            self._stop_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
        self._handling_retry = False
        self._clear_frames = 0
        auto.resume_interactions()
        if thread is not None:
            log.debug("通用服务器重试监控线程已停止")

    def _load_templates(self) -> tuple[np.ndarray, ...]:
        templates = []
        for path in self.TEMPLATE_PATHS:
            template = ImageUtils.load_from_specific_path(self.RETRY_TEMPLATE, path)
            if template is not None:
                templates.append(template)
        return tuple(templates)

    @staticmethod
    def _to_gray_array(screenshot) -> np.ndarray:
        image = np.asarray(screenshot)
        if image.ndim == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return image

    def _find_retry_button(self, screenshot) -> tuple[int, int] | None:
        image = self._to_gray_array(screenshot)
        best_center = None
        best_score = 0.9
        for template in self._templates:
            match = ImageUtils.match_template(image, template, None, model="clam")
            if match is None:
                continue
            center, score = match
            if score >= best_score:
                best_center = center
                best_score = score
        return best_center

    def check_once(self, screenshot=None) -> bool:
        """检查一次重试弹窗，返回本轮是否执行了点击。"""
        if screenshot is None:
            screenshot = auto.take_monitor_screenshot()
        if screenshot is None:
            return False
        if auto.check_pause() and not self._handling_retry:
            return False

        retry_position = self._find_retry_button(screenshot)
        if retry_position is None:
            if self._handling_retry:
                self._clear_frames += 1
                if self._clear_frames >= 2:
                    self._handling_retry = False
                    self._clear_frames = 0
                    auto.resume_interactions()
                    log.debug("服务器错误弹窗已消失，恢复业务点击")
            return False

        self._clear_frames = 0
        if not self._handling_retry:
            self._handling_retry = True
            auto.suspend_interactions()
            log.debug("服务器错误弹窗处理中，暂时阻止业务点击")

        if auto.check_pause():
            return False

        now = time.monotonic()
        if now - self._last_click_time < self.click_cooldown:
            return False

        auto.monitor_mouse_click(retry_position[0], retry_position[1])
        self._last_click_time = now
        log.warning(f"检测到服务器错误弹窗，监控线程已点击重试: {retry_position}")
        return True

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_interval):
            try:
                self.check_once()
            except Exception:
                log.exception("通用服务器重试监控线程处理异常")


retry_monitor = RetryMonitor()
