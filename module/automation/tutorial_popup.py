"""新手教程弹窗的全局检测与关闭。"""

import time
from typing import TYPE_CHECKING

import cv2
import numpy as np

from module.config import cfg
from module.logger import log
from utils.image_utils import ImageUtils

from ..game_and_screen import screen
from .screenshot import ScreenShot

if TYPE_CHECKING:
    from PIL import Image


class TutorialPopupMixin:
    """新手教程弹窗检测与关闭能力，由 ``Automation`` 继承。

    依赖宿主类（``Automation``）提供：``screenshot``、``last_screenshot_time``、
    ``img_cache``、``memory_protection``、``_screenshot_lock``、
    ``_load_template_for_path()``、``_is_valid_match()``、``_remember_screenshot()``、
    ``mouse_action_with_pos()``。
    """

    #: 相对位置的基准分辨率：关闭按钮的位置是在这个分辨率下量出来的
    #: （与项目模板 2560×1440 基准一致）
    TUTORIAL_REFERENCE_SIZE: tuple[int, int] = (2560, 1440)

    #: 关闭位置：以 :attr:`TUTORIAL_REFERENCE_SIZE` 为基准量出的像素位置，
    #: 运行时会换算成**相对比例**再乘以当前画面尺寸，所以任意分辨率/窗口大小
    #: 都落在同一个相对位置上（例如 1080p 下会自动变成 150,71）。
    #: 元组含义是 (宽, 高) 即 (x, y)：200 是横向、95 是纵向。
    TUTORIAL_CLICK_REFERENCE_POS: tuple[int, int] = (200, 95)

    #: 教程弹窗模板（相对 ``assets/images/<主题>/<语言>/`` 的路径）
    TUTORIAL_TEMPLATES: tuple[str, ...] = (
        "base/tutorial_achievements_assets.png",
        "base/tutorial_mirror_assets.png",
        "base/tutorial_pass_assets.png",
        "base/tutorial_team_assets.png",
    )

    #: 模板已裁掉黑底并限定搜索区域，命中时相似度通常很高；取 0.9 降低误点风险，
    #: 日志里会打印实际相似度，可据此微调
    TUTORIAL_THRESHOLD: float = 0.90

    #: 模拟器（手机版）放宽阈值：手游 UI 与 PC 不完全一致（教程标题、返回键的
    #: 字形与排版不同），同一套模板只能匹配到 0.6x。
    #: 实测 MuMu 英文版编队教程最高 0.680，同屏其它三个教程模板最高 0.544~0.574。
    TUTORIAL_THRESHOLD_SIMULATOR: float = 0.65

    #: 模拟器放宽阈值时必须同时满足：最佳模板要比第二名高出这么多分，
    #: 否则宁可不点 —— 避免把"另一条教程/其它浮层"误判成本模板
    TUTORIAL_SIMULATOR_MARGIN: float = 0.06

    #: 同一个弹窗最多连续点击次数，超过后进入冷却，避免无脑连点
    TUTORIAL_MAX_CLICKS: int = 2
    #: 两次点击之间的最小间隔（秒）
    TUTORIAL_CLICK_INTERVAL: float = 1.5
    #: 连续点击仍未关闭时的冷却时间（秒）
    TUTORIAL_RETRY_COOLDOWN: float = 5.0
    #: 点击后等待界面刷新的时间（秒），随后重新截图验证
    TUTORIAL_VERIFY_DELAY: float = 0.5
    #: 识别模式的日志标签
    TUTORIAL_MODEL: str = "clam"

    def _tutorial_state(self) -> dict:
        """懒初始化运行期状态，避免改动宿主类 ``__init__``。"""
        state = getattr(self, "_tutorial_state_data", None)
        if state is None:
            state = {
                "clicks": 0,  # 当前弹窗已连续点击次数
                "last_click": 0.0,  # 上次点击时间（monotonic）
                "cooldown_until": 0.0,  # 冷却截止时间（monotonic）
                "reported": set(),  # 已提示过的模板，避免日志刷屏
                "busy": False,  # 防止验证截图递归
            }
            self._tutorial_state_data = state
        return state

    def clear_tutorial_cache(self) -> None:
        """重置教程弹窗状态。

        模板本体缓存在宿主 ``img_cache`` 里（``_load_template_for_path`` 负责），
        所以这里只需清理一次性告警记录与点击计数。
        """
        state = self._tutorial_state()
        state["reported"].clear()
        state["clicks"] = 0
        state["cooldown_until"] = 0.0

    @staticmethod
    def _tutorial_gray(frame):
        """把截图统一成灰度 ndarray，与模板通道保持一致。"""
        if frame is None:
            return None
        image = np.asarray(frame)
        if image.size == 0:
            return None
        if image.ndim == 3:
            if image.shape[2] == 1:
                image = image[:, :, 0]
            else:
                image = cv2.cvtColor(image[:, :, :3], cv2.COLOR_RGB2GRAY)
        return image

    def find_tutorial_popup(self, screenshot=None):
        """检测当前画面里的新手教程弹窗。

        Args:
            screenshot: 待检测的帧；``None`` 时使用 ``self.screenshot``。

        Returns:
            ``(模板名, 匹配中心)``；未命中返回 ``None``。
            匹配中心是模板黑底裁边后条幅的中心（约在画面左上区域），仅用于日志，
            不参与点击定位 —— 点击位置由相对比例
            ``TUTORIAL_CLICK_REFERENCE_POS / TUTORIAL_REFERENCE_SIZE`` 决定。
        """
        state = self._tutorial_state()
        frame = screenshot if screenshot is not None else getattr(self, "screenshot", None)
        target_image = self._tutorial_gray(frame)
        if target_image is None:
            return None

        # ``memory_protection`` 是 Automation.__init__ 里设置的开关，测试替身可能没有
        if getattr(self, "memory_protection", False):
            import psutil

            if psutil.virtual_memory().percent > 90:
                self.clear_img_cache()

        strict = self.TUTORIAL_THRESHOLD
        relaxed = (
            min(self.TUTORIAL_THRESHOLD_SIMULATOR, strict) if cfg.simulator else strict
        )
        threshold_label = (
            f"{strict:.2f}(模拟器放宽 {relaxed:.2f})" if relaxed < strict else f"{strict:.2f}"
        )
        # 收集整帧候选分数：模拟器放宽阈值时要用"最佳 vs 次佳"的差距做二次判定
        scores: list[tuple[float, str, tuple[int, int]]] = []

        for target in self.TUTORIAL_TEMPLATES:
            for loaded_path in ImageUtils.existing_image_paths(target):
                template, bbox = self._load_template_for_path(target, loaded_path, True)
                if template is None:
                    continue
                # 模板比截图还大时 cv2 会直接抛错，这里提前跳过，且只提示一次
                if template.shape[0] > target_image.shape[0] or template.shape[1] > target_image.shape[1]:
                    if target not in state["reported"]:
                        state["reported"].add(target)
                        log.debug(
                            f"教程弹窗模板大于当前截图，跳过:{target} "
                            f"{template.shape[:2]} > {target_image.shape[:2]}",
                            stacklevel=3,
                        )
                    continue

                match = ImageUtils.match_template(target_image, template, bbox, self.TUTORIAL_MODEL)
                if match is None:
                    continue
                center, match_val = match
                match_val = float(match_val)
                # 严格阈值命中立刻返回（PC 与模拟器同一套行为，性能也不变）
                if self._is_valid_match(match_val, strict):
                    log.debug(
                        f"教程弹窗命中:{target} 路径:{loaded_path} 相似度:{match_val:.3f}",
                        stacklevel=3,
                    )
                    return target, center
                scores.append((match_val, target, center))
                log.debug(
                    f"教程弹窗未命中:{target} 路径:{loaded_path} "
                    f"相似度:{match_val:.3f} 阈值:{threshold_label}",
                    stacklevel=3,
                )

        # 模拟器兜底：全部模板都没到严格阈值时，若最佳模板明显优于其它模板，仍判定命中
        if relaxed < strict and scores:
            scores.sort(key=lambda item: item[0], reverse=True)
            best_val, best_target, best_center = scores[0]
            runner_up = scores[1][0] if len(scores) > 1 else 0.0
            gap = best_val - runner_up
            if best_val >= relaxed and gap >= self.TUTORIAL_SIMULATOR_MARGIN:
                log.info(
                    f"模拟器放宽阈值命中教程弹窗:{best_target} 相似度:{best_val:.3f}"
                    f"（次佳 {runner_up:.3f}，差值 {gap:.3f} >= "
                    f"{self.TUTORIAL_SIMULATOR_MARGIN:.2f}，阈值 {relaxed:.2f}）",
                    stacklevel=3,
                )
                return best_target, best_center
            if best_val >= relaxed:
                log.debug(
                    f"模拟器候选被否决:{best_target} 相似度:{best_val:.3f} "
                    f"次佳:{runner_up:.3f} 差值 {gap:.3f} < {self.TUTORIAL_SIMULATOR_MARGIN:.2f}",
                    stacklevel=3,
                )
        return None

    @classmethod
    def tutorial_click_ratio(cls) -> tuple[float, float]:
        """返回关闭按钮相对画面的比例 ``(宽占比, 高占比)``。

        由 :attr:`TUTORIAL_CLICK_REFERENCE_POS` 与
        :attr:`TUTORIAL_REFERENCE_SIZE` 相除得到，与具体分辨率无关。
        """
        ref_width, ref_height = cls.TUTORIAL_REFERENCE_SIZE
        ref_x, ref_y = cls.TUTORIAL_CLICK_REFERENCE_POS
        return ref_x / ref_width, ref_y / ref_height

    def _tutorial_client_size(self) -> tuple[int, int]:
        """当前画面尺寸（非模拟器为客户区，模拟器为模拟器画面）。"""
        if cfg.simulator:
            shot = getattr(self, "screenshot", None)
            size = getattr(shot, "size", None)
            if size is not None and len(size) == 2 and size[0] > 0 and size[1] > 0:
                return int(size[0]), int(size[1])
            height = int(cfg.set_win_size or self.TUTORIAL_REFERENCE_SIZE[1])
            return int(height * 16 / 9), height
        left, top, right, bottom = screen.handle.rect(True)
        return int(right - left), int(bottom - top)

    def tutorial_click_position(self) -> tuple[int, int]:
        """按**相对位置**计算关闭按钮在当前画面里的客户区坐标。

        不再依赖"某一分辨率下的绝对屏幕坐标"：先用
        ``TUTORIAL_CLICK_REFERENCE_POS / TUTORIAL_REFERENCE_SIZE`` 得到比例，
        再乘以当前客户区（或模拟器画面）的宽高。
        - 2560×1440 → (200, 95)
        - 1920×1080 → (150, 71)
        - 1280×720  → (100, 48)
        窗口位置/标题栏厚度不再影响结果，因为比例直接作用在客户区尺寸上。
        """
        ratio_x, ratio_y = self.tutorial_click_ratio()
        try:
            width, height = self._tutorial_client_size()
        except Exception as e:
            log.warning(f"获取教程弹窗点击基准尺寸失败:{e}", stacklevel=3)
            width, height = 0, 0
        if width <= 0 or height <= 0:
            ref_x, ref_y = self.TUTORIAL_CLICK_REFERENCE_POS
            log.warning(
                f"无法获取当前画面尺寸，教程弹窗点击回退到基准坐标({ref_x},{ref_y})",
                stacklevel=3,
            )
            return int(ref_x), int(ref_y)

        # 四舍五入用 +0.5 取整，避免 Python 银行家舍入在 .5 处的跳变
        client_x = int(ratio_x * width + 0.5)
        client_y = int(ratio_y * height + 0.5)
        client_x = min(max(client_x, 0), width - 1)
        client_y = min(max(client_y, 0), height - 1)
        return client_x, client_y

    def _tutorial_grab_frame(self):
        """点击后重新截一帧用于验证，绕过截图间隔与弹窗检查。"""
        try:
            with self._screenshot_lock:
                return ScreenShot.take_screenshot(True)
        except Exception as e:
            log.debug(f"教程弹窗验证截图失败:{e}", stacklevel=3)
            return None

    def handle_tutorial_popups(self, screenshot=None):
        """检测并关闭教程弹窗（点击后重新截图确认）。

        Args:
            screenshot: 本轮新截的帧；``None`` 时使用当前帧。

        Returns:
            已确认弹窗消失后的新帧；本轮未点击或无法确认时返回 ``None``。
        """
        state = self._tutorial_state()
        if state["busy"]:
            return None

        now = time.monotonic()
        if now < state["cooldown_until"]:
            return None
        if state["clicks"] and now - state["last_click"] < self.TUTORIAL_CLICK_INTERVAL:
            return None

        found = self.find_tutorial_popup(screenshot)
        if found is None:
            state["clicks"] = 0
            return None

        target, _center = found
        state["busy"] = True
        try:
            client_x, client_y = self.tutorial_click_position()
            ratio_x, ratio_y = self.tutorial_click_ratio()
            log.info(
                f"检测到新手教程弹窗:{target}，点击关闭 相对位置({ratio_x:.2%},{ratio_y:.2%})"
                f" -> 客户区({client_x},{client_y})",
                stacklevel=3,
            )
            self.mouse_action_with_pos((client_x, client_y), offset=False, action="click")
            state["last_click"] = time.monotonic()
            state["clicks"] += 1

            time.sleep(self.TUTORIAL_VERIFY_DELAY)
            fresh = self._tutorial_grab_frame()
            if fresh is None:
                log.debug("教程弹窗点击后截图失败，等待下一次截图再确认", stacklevel=3)
            elif self.find_tutorial_popup(fresh) is None:
                # 确认消失：把这一帧交给调用方，避免继续使用带弹窗的旧帧
                state["clicks"] = 0
                state["cooldown_until"] = 0.0
                self.screenshot = fresh
                self.last_screenshot_time = time.time()
                self._remember_screenshot(fresh)
                log.info("新手教程弹窗已关闭", stacklevel=3)
                return fresh

            if state["clicks"] >= self.TUTORIAL_MAX_CLICKS:
                state["clicks"] = 0
                state["cooldown_until"] = time.monotonic() + self.TUTORIAL_RETRY_COOLDOWN
                log.warning(
                    f"教程弹窗连续点击仍未消失，暂停处理 {self.TUTORIAL_RETRY_COOLDOWN:.0f}s"
                    f"（请检查点击位置 基准{self.TUTORIAL_CLICK_REFERENCE_POS}"
                    f"@ {self.TUTORIAL_REFERENCE_SIZE} 或阈值 {self.TUTORIAL_THRESHOLD}）",
                    stacklevel=3,
                )
            else:
                log.debug("教程弹窗仍在，下一次截图后重试点击", stacklevel=3)
            return None
        finally:
            state["busy"] = False