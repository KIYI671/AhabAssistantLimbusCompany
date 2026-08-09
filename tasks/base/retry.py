import re
import time
from dataclasses import dataclass
from time import sleep

import cv2
import numpy as np

from module.automation import auto
from module.config import cfg
from module.game_and_screen import screen
from module.logger import log
from utils.utils import check_game_running

_last_title_screen_tap_time = 0.0
_last_simulator_alive_check_time = 0.0
_last_server_error_retry_time = 0.0
_server_error_disabled_since: float | None = None

SERVER_ERROR_RETRY_INTERVAL = 5.0
SERVER_ERROR_DISABLED_TIMEOUT = 15.0


@dataclass(frozen=True)
class ServerErrorDialog:
    close_position: tuple[int, int]
    close_bounds: tuple[int, int, int, int]
    retry_position: tuple[int, int]
    retry_bounds: tuple[int, int, int, int]


def _entry_with_text(
    entries: list[tuple[str, tuple[int, int, int, int]]], target: str
) -> tuple[str, tuple[int, int, int, int]] | None:
    return next((entry for entry in entries if target in entry[0]), None)


def find_server_error_dialog(
    entries: list[tuple[str, tuple[int, int, int, int]]],
) -> ServerErrorDialog | None:
    """从当前帧 OCR 结果中识别新版中文服务器错误弹窗。"""
    error = _entry_with_text(entries, "服务器发生错误")
    later = _entry_with_text(entries, "请稍后再试")
    close = _entry_with_text(entries, "关闭")
    retry = _entry_with_text(entries, "重试")
    if not all((error, later, close, retry)):
        return None

    _, error_bounds = error
    _, later_bounds = later
    _, close_bounds = close
    _, retry_bounds = retry
    close_position = ((close_bounds[0] + close_bounds[2]) // 2, (close_bounds[1] + close_bounds[3]) // 2)
    retry_position = ((retry_bounds[0] + retry_bounds[2]) // 2, (retry_bounds[1] + retry_bounds[3]) // 2)
    message_bottom = max(error_bounds[3], later_bounds[3])
    if retry_position[0] <= close_position[0] or min(close_position[1], retry_position[1]) <= message_bottom:
        return None

    return ServerErrorDialog(close_position, close_bounds, retry_position, retry_bounds)


def is_retry_button_enabled(image: np.ndarray, bounds: tuple[int, int, int, int]) -> bool:
    """根据新版按钮金色文字的饱和度判断“重试”是否仍可点击。"""
    x1, y1, x2, y2 = bounds
    height, width = image.shape[:2]
    crop = image[max(0, y1 - 4) : min(height, y2 + 4), max(0, x1 - 4) : min(width, x2 + 4)]
    if crop.size == 0:
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gold_pixels = (hsv[:, :, 1] > 20) & (hsv[:, :, 2] > 100)
    return int(gold_pixels.sum()) >= 8


def _is_server_error_retry_countdown(entries: list[tuple[str, tuple[int, int, int, int]]]) -> bool:
    return any("重试" in text and re.search(r"重试\s*\d+", text) for text, _ in entries)


def handle_server_error_dialog(now: float | None = None) -> bool | None:
    """处理服务器错误：True 为已拦截重试，False 为关闭重启，None 为非目标弹窗。"""
    global _last_server_error_retry_time, _server_error_disabled_since

    entries = auto.get_ocr_entries()
    dialog = find_server_error_dialog(entries)
    if dialog is None:
        _server_error_disabled_since = None
        return None

    now = time.time() if now is None else now
    if _is_server_error_retry_countdown(entries):
        _server_error_disabled_since = None
        log.info("服务器错误弹窗的重试正在游戏倒计时中，等待按钮恢复可点击")
        return True

    color_screenshot = auto.color_screenshot
    if color_screenshot is None:
        log.warning("检测到服务器错误弹窗，但当前帧缺少彩色截图，等待下一帧后再处理")
        return True

    image = np.asarray(color_screenshot.convert("RGB") if hasattr(color_screenshot, "convert") else color_screenshot)
    if is_retry_button_enabled(image, dialog.retry_bounds):
        _server_error_disabled_since = None
        if now - _last_server_error_retry_time >= SERVER_ERROR_RETRY_INTERVAL:
            log.info("检测到服务器错误弹窗，点击重试")
            auto.mouse_click(*dialog.retry_position)
            _last_server_error_retry_time = now
        else:
            log.debug("服务器错误弹窗的重试仍在 AALC 5 秒节流窗口内")
        return True

    if _server_error_disabled_since is None:
        _server_error_disabled_since = now
        log.info("服务器错误弹窗的重试暂不可用，等待其恢复")
        return True
    if now - _server_error_disabled_since < SERVER_ERROR_DISABLED_TIMEOUT:
        log.debug("服务器错误弹窗的重试仍不可用，继续等待")
        return True

    log.warning("服务器错误弹窗的重试长时间不可用，关闭弹窗并重启游戏")
    auto.mouse_click(*dialog.close_position)
    _server_error_disabled_since = None
    kill_game()
    restart_game()
    return False


def ensure_simulator_game_started() -> bool:
    """模拟器模式下确认游戏仍在前台，不在时尝试拉起游戏。"""
    global _last_simulator_alive_check_time
    if not cfg.simulator:
        return False

    now = time.time()
    if now - _last_simulator_alive_check_time < 5:
        return False
    _last_simulator_alive_check_time = now

    if cfg.simulator_type == 0:
        from module.automation.input_handlers.simulator.mumu_control import (
            MumuControl,
        )

        connection_device = MumuControl.connection_device
    else:
        from module.automation.input_handlers.simulator.simulator_control import (
            SimulatorControl,
        )

        connection_device = SimulatorControl.connection_device

    if connection_device is None:
        return False

    if connection_device.check_game_alive():
        return False

    log.info("检测到游戏未运行或不在前台，尝试自动启动游戏")
    connection_device.start_game()
    sleep(3)
    return True


def click_title_screen_safely() -> None:
    """标题页点击入口，避开账号、清缓存和中间弹窗区域。"""
    global _last_title_screen_tap_time
    if not cfg.simulator:
        auto.mouse_click_blank()
        return

    now = time.time()
    if now - _last_title_screen_tap_time < 15:
        return
    _last_title_screen_tap_time = now

    height = int(cfg.set_win_size or 1080)
    width = int(height * 16 / 9)
    tap_points = ((0.86, 0.80), (0.74, 0.83), (0.91, 0.58))
    index = int(now // 10) % len(tap_points)
    x_ratio, y_ratio = tap_points[index]
    auto.mouse_click(int(width * x_ratio), int(height * y_ratio))


def kill_game():
    """关闭游戏；Windows 路径委托公共优雅关闭逻辑。"""
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            MumuControl.connection_device.close_current_app()
        else:
            from module.automation.input_handlers.simulator.simulator_control import (
                SimulatorControl,
            )

            SimulatorControl.connection_device.close_current_app()
        return

    from module.game_and_screen import game_process

    game_process.close_game()


def check_times(start_time, timeout=90, logs=True):
    """检查是否卡死超时，若是则尝试关闭重启游戏"""
    now_time = time.time()
    if logs and int(now_time - start_time) > 9 and int(now_time - start_time) % 10 == 0:
        log.info(f"初始时间为{time.strftime('%H:%M:%S', time.localtime(start_time))}，此刻时间为{time.strftime('%H:%M:%S', time.localtime(now_time))}，已卡死{int(now_time - start_time)}秒")
        sleep(1)
    if now_time - start_time > timeout:
        log.info(f"已卡死超过{timeout}秒，尝试关闭重启游戏")
        kill_game()
        restart_game()
        return True
    else:
        return False


def retry():
    """重试连接。

    为保证稳定性，retry 内循环始终刷新截图，避免复用旧帧导致误判。
    """
    start_time = time.time()
    is_windows = not cfg.config.simulator
    if is_windows:
        saved_hwnd = screen.handle.hwnd
    while True:
        if ensure_simulator_game_started():
            start_time = time.time()
            continue
        if is_windows and screen.handle.hwnd != saved_hwnd:
            # 句柄发生变化则重置初始时间, 以免误判卡死
            saved_hwnd = screen.handle.hwnd
            start_time = time.time()
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if check_times(start_time):
            return False
        if auto.take_screenshot_with_color() is None:
            continue
        server_error_result = handle_server_error_dialog()
        if server_error_result is False:
            return False
        if server_error_result is True:
            continue
        if auto.find_element("base/connecting_assets.png"):
            continue
        if position := auto.find_element("base/retry_countdown.png"):
            sleep(5)
            auto.mouse_click(position[0], position[1], times=3)
            continue
        if auto.click_element("base/retry.png", threshold=0.9):
            auto.mouse_to_blank()
            continue
        if (
            auto.find_element("base/retry_countdown.png")
            or auto.find_element("base/retry.png")
            or auto.find_element("base/try_again.png")
        ):
            auto.click_element("base/retry.png", threshold=0.9)
            continue
        if auto.find_element("base/clear_all_caches_assets.png", model="clam"):
            if auto.click_element("base/update_confirm_assets.png"):
                continue
            click_title_screen_safely()
            continue
        if auto.click_element("base/only_option_assets.png", model="clam"):
            sleep(5)
            if not check_game_running():
                log.debug("检测到游戏未运行，调用 init_game() 重新初始化")
                from tasks.base.script_task_scheme import init_game

                init_game()
            continue
        break


def restart_game():
    """重启游戏"""
    from tasks.base.back_init_menu import back_init_menu
    from tasks.base.script_task_scheme import init_game

    init_game()
    sleep(3)
    back_init_menu()
