import os
import webbrowser
from time import sleep, time

import psutil
import win32gui

from module.config import cfg
from utils.singletonmeta import SingletonMeta


class Game(metaclass=SingletonMeta):
    def __init__(self, logger):
        self.game_path = cfg.game_path
        self.game_url = "steam://rungameid/1973530"
        self.log = logger
        self.process_name = cfg.game_process_name
        self.game_path_exists = True
        self.last_check_time = None
        self.check_in_short_time = 0

    def check_game_alive(self):
        """检查游戏是否存活：进程与主窗口都在才算存活。

        仅有进程不等于游戏正常——崩溃残留的"僵尸进程"没有窗口，
        会骗过启动逻辑导致永远无法真正重启，这里顺手清理。
        刚启动的游戏还没来得及创建窗口，给宽限期避免误杀。
        """
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                # 获取进程的可执行文件名（如 "notepad.exe"）
                proc_name = proc.info["name"]
                # 精确匹配进程名（区分大小写，取决于系统）
                if self.process_name in proc_name:
                    if win32gui.FindWindow("UnityWndClass", cfg.game_title_name):
                        self.log.debug(f"游戏已启动：{self.process_name}，进程ID：{proc.pid}")
                        return True
                    if time() - proc.create_time() < 180:
                        # 正在启动的游戏进程窗口尚未创建，视为存活
                        return True
                    # 进程在但窗口长期缺失 = 僵尸进程，清理后以便重新启动
                    self.log.warning(f"发现无窗口的僵尸游戏进程 {proc.pid}，正在清理")
                    psutil.Process(proc.pid).kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略已终止、无权限或僵尸进程
                continue
        return False

    def start_game(self) -> bool:
        """启动游戏"""
        if self.check_game_alive():
            if self.last_check_time is None or time() - self.last_check_time > 60:
                self.last_check_time = time()
                self.check_in_short_time = 0
            else:
                self.check_in_short_time += 1
            if self.check_in_short_time > 5:
                from tasks.base.retry import kill_game

                kill_game()
                self.check_in_short_time = 0
            else:
                return True

        if not os.path.exists(self.game_path):
            self.log.error(f"游戏路径不存在：{self.game_path}，使用steam命令启动...")
            self.game_path_exists = False

        try:
            # 调用系统打开该 URL（会触发 Steam 启动游戏）
            webbrowser.open(self.game_url)
            self.log.info("使用steam命令启动游戏")
            sleep(5)
            if not self.check_game_alive() and self.game_path_exists:
                os.startfile(self.game_path)
                self.log.info(f"游戏启动：{self.game_path}")
            return True
        except Exception as e:
            self.log.error(f"启动游戏时发生错误：{e}")
        return False
