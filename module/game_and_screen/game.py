import os
import subprocess
import webbrowser
from time import monotonic, sleep

import psutil
import win32con
import win32gui

from module.config import cfg
from module.game_and_screen.steam_cloud import handle_steam_cloud_sync_dialog
from utils.singletonmeta import SingletonMeta

GAME_GRACEFUL_CLOSE_TIMEOUT_SECONDS = 30.0


class Game(metaclass=SingletonMeta):
    def __init__(self, logger):
        self.game_path = cfg.game_path
        self.game_url = "steam://rungameid/1973530"
        self.log = logger
        self.process_name = cfg.game_process_name
        self.game_path_exists = True
        self._launch_requested_at: float | None = None
        self._cloud_sync_confirmation_attempted = False
        self._invalid_path_logged = False

    def check_game_alive(self):
        for proc in psutil.process_iter(["name"]):
            try:
                # 获取进程的可执行文件名（如 "notepad.exe"）
                proc_name = proc.info["name"]
                if proc_name and self.process_name.casefold() == proc_name.casefold():
                    self.log.debug(f"游戏已启动：{self.process_name}，进程ID：{proc.pid}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略已终止、无权限或僵尸进程
                continue
        return False

    def start_game(self) -> bool:
        """发起一次游戏启动；等待中的请求绝不重复唤起 Steam。"""
        if self._launch_requested_at is not None:
            return True

        self._cloud_sync_confirmation_attempted = False
        self._launch_requested_at = monotonic()
        if self.check_game_alive():
            self.log.info("检测到游戏进程正在运行，等待窗口就绪")
            return True
        self.game_path_exists = os.path.exists(self.game_path)
        try:
            if self.game_path_exists:
                os.startfile(self.game_path)
                self.log.info(f"使用本地路径启动游戏：{self.game_path}")
            else:
                if not self._invalid_path_logged:
                    self.log.warning(f"游戏路径不存在：{self.game_path}，将使用 Steam 启动；请在设置中更新游戏路径")
                    self._invalid_path_logged = True
                webbrowser.open(self.game_url)
                self.log.info("使用 Steam 命令启动游戏")
            return True
        except Exception as e:
            self.finish_launch_attempt()
            self.log.error(f"启动游戏时发生错误：{e}")
            return False

    def handle_pending_launch(self) -> bool:
        """处理一次尚未得到游戏窗口的启动请求中的 Steam 云同步确认。"""
        if self._launch_requested_at is None or self._cloud_sync_confirmation_attempted:
            return False

        def _consume_confirmation() -> None:
            self._cloud_sync_confirmation_attempted = True

        handled = handle_steam_cloud_sync_dialog(on_dialog_detected=_consume_confirmation)
        if handled:
            self.log.warning("检测到 Steam 云同步失败，已自动点击“仍然进行游戏”继续无人值守启动")
        return handled

    def finish_launch_attempt(self) -> None:
        """清除本次启动请求状态，让后续恢复可发起新的单次尝试。"""
        self._launch_requested_at = None
        self._cloud_sync_confirmation_attempted = False

    def close_game(self) -> bool:
        """优先正常关闭游戏，超过宽限期后才强制结束进程。"""
        self.finish_launch_attempt()
        if not self.check_game_alive():
            self.log.info("跳过退出游戏：游戏进程未运行")
            return True

        try:
            from module.game_and_screen import screen

            hwnd = screen.handle.hwnd
            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                self.log.info("已请求游戏正常退出，等待 Steam 同步")
        except Exception as e:
            self.log.warning(f"请求游戏正常退出失败，将等待后再尝试强制结束：{e}")

        deadline = monotonic() + GAME_GRACEFUL_CLOSE_TIMEOUT_SECONDS
        while self.check_game_alive() and monotonic() < deadline:
            sleep(1)
        if not self.check_game_alive():
            self.log.info("游戏已正常退出")
            return True

        self.log.warning("等待游戏正常退出超时，改为强制结束进程")
        result = subprocess.run(["taskkill", "/F", "/IM", self.process_name], check=False, capture_output=True, text=True)
        if result.returncode == 0:
            self.log.info("已强制结束游戏进程")
            return True
        detail = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
        self.log.error(f"强制结束游戏进程失败：{detail}")
        return False
