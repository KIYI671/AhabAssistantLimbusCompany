"""新手教程弹窗的全局检测与关闭。

模板位置：``assets/images/<主题>/<语言>/base/tutorial_*_assets.png``。
模板特征（实测记录，未做猜测）：

* 2560×1440 的 **RGBA** 图，alpha 全为 255（不透明），按 AALC 惯例丢弃 alpha 只取 RGB；
* RGB 画面约 98% 是纯黑背景，真正有内容的区域是顶部一条横向条幅
  （例如 zh_cn 成就条 bbox 为 ``(107, 33, 834, 158)``，en 版本会因文字更长而更宽），
  因此完全符合 ``*_assets.png`` 约定：``_load_template_for_path`` 会用
  ``ImageUtils.get_bbox`` 裁掉黑底，并把该 bbox 当作搜索区域；
  ``clam`` 模式只在其外扩 ±30px 的范围内匹配，速度快、误匹配少；
* 同一模板的 dark/default、zh_cn/en 之间差异 0.3%~1.5%，只体现主题与文字差异，
  所以按主题/语言各存一份即可。

检测挂接点：``Automation.take_screenshot()``。每一帧新截图都会先过这里；
命中就点击关闭、随后重新截图确认弹窗消失，确认后才把新帧交给调用方。
因此所有调用 ``auto.take_screenshot()`` 的自动化流程都会自动获得该能力，
任务代码不需要改动。

复用说明（不重复造轮子）：

* 识别：``ImageUtils.existing_image_paths`` 选路径、``Automation._load_template_for_path``
  加载+裁边+缓存、``ImageUtils.match_template`` 做 TM_CCOEFF_NORMED、
  ``Automation._is_valid_match`` 做阈值判定 —— 与 ``find_image_element`` 完全同一条链路；
* 点击：``Automation.mouse_action_with_pos``（含交互门/输入锁/点击间隔），
  坐标换算复用 ``Handle.mouse_pos_to_client_mouse``；
* 截图：``ScreenShot.take_screenshot``（与业务截图同一后端）；
* 日志/节流：``module.logger.log``、``cfg``。
"""

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

    #: 教程弹窗模板（相对 ``assets/images/<主题>/<语言>/`` 的路径）
    TUTORIAL_TEMPLATES: tuple[str, ...] = (
        "base/tutorial_achievements_assets.png",
        "base/tutorial_mirror_assets.png",
        "base/tutorial_pass_assets.png",
        "base/tutorial_team_assets.png",
    )

    #: 关闭位置：**屏幕坐标**，原点为屏幕左上角，四个弹窗共用且固定不变。
    #: 元组含义是 (宽, 高)，也就是 (x, y)：第一个数字 200 是横向偏移（距屏幕左边缘），
    #: 第二个数字 95 是纵向偏移（距屏幕上边缘）。
    TUTORIAL_CLICK_SCREEN_POS: tuple[int, int] = (200, 95)

    #: 模板已裁掉黑底并限定搜索区域，命中时相似度通常很高；取 0.9 降低误点风险，
    #: 日志里会打印实际相似度，可据此微调
    TUTORIAL_THRESHOLD: float = 0.90

    #: 同一个弹窗最多连续点击次数，超过后进入冷却，避免无脑连点
    TUTORIAL_MAX_CLICKS: int = 2
    #: 两次点击之间的最小间隔（秒）
    TUTORIAL_CLICK_INTERVAL: float = 1.5
    #: 连续点击仍未关闭时的冷却时间（秒）
    TUTORIAL_RETRY_COOLDOWN: float = 30.0
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
            不参与点击定位 —— 点击位置由 ``TUTORIAL_CLICK_SCREEN_POS`` 决定。
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
                if not self._is_valid_match(match_val, self.TUTORIAL_THRESHOLD):
                    log.debug(
                        f"教程弹窗未命中:{target} 路径:{loaded_path} "
                        f"相似度:{match_val:.3f} 阈值:{self.TUTORIAL_THRESHOLD:.2f}",
                        stacklevel=3,
                    )
                    continue
                log.debug(
                    f"教程弹窗命中:{target} 路径:{loaded_path} 相似度:{match_val:.3f}",
                    stacklevel=3,
                )
                return target, center
        return None

    def tutorial_click_position(self) -> tuple[int, int]:
        """把配置的**屏幕坐标**换算成项目统一使用的**客户区坐标**。

        坐标元组是 ``(宽, 高)`` 即 ``(x, y)``，原点固定在屏幕左上角：
        第一个数字向右增大，第二个数字向下增大。
        非模拟器：客户区坐标 = 屏幕坐标 - 客户区左上角屏幕坐标，复用
        ``Handle.mouse_pos_to_client_mouse``；越界时裁剪到客户区内，
        避免窗口带标题栏或未全屏时点到客户区外面。
        模拟器：没有 Windows 窗口句柄，坐标按模拟器像素直接使用。
        """
        screen_x, screen_y = self.TUTORIAL_CLICK_SCREEN_POS
        if cfg.simulator:
            return int(screen_x), int(screen_y)

        client_x, client_y = screen.handle.mouse_pos_to_client_mouse(screen_x, screen_y)
        try:
            left, top, right, bottom = screen.handle.rect(True)
            width, height = right - left, bottom - top
        except Exception:
            width, height = 0, 0
        if width > 0 and height > 0 and not (0 <= client_x < width and 0 <= client_y < height):
            log.warning(
                f"教程弹窗点击位置屏幕{self.TUTORIAL_CLICK_SCREEN_POS} 超出客户区"
                f"({left},{top},{right},{bottom})，已裁剪到边界",
                stacklevel=3,
            )
            client_x = min(max(client_x, 0), width - 1)
            client_y = min(max(client_y, 0), height - 1)
        return int(client_x), int(client_y)

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
            log.info(
                f"检测到新手教程弹窗:{target}，点击关闭 屏幕{self.TUTORIAL_CLICK_SCREEN_POS}"
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
                    f"（请检查点击位置 {self.TUTORIAL_CLICK_SCREEN_POS} 或阈值 {self.TUTORIAL_THRESHOLD}）",
                    stacklevel=3,
                )
            else:
                log.debug("教程弹窗仍在，下一次截图后重试点击", stacklevel=3)
            return None
        finally:
            state["busy"] = False