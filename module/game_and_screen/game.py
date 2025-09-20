import os
import webbrowser

import psutil

from module.config import cfg
from utils.singletonmeta import SingletonMeta


class Game(metaclass=SingletonMeta):
    def __init__(self, logger):
        self.game_path = cfg.game_path
        self.game_url = "steam://rungameid/1973530"
        self.log = logger
        self.process_name = cfg.game_process_name
        self.game_path_exists = True

    def start_game(self) -> bool:
        """启动游戏"""
        for proc in psutil.process_iter(['name']):
            try:
                # 获取进程的可执行文件名（如 "notepad.exe"）
                proc_name = proc.info['name']
                # 精确匹配进程名（区分大小写，取决于系统）
                if self.process_name in proc_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略已终止、无权限或僵尸进程
                continue

        if not os.path.exists(self.game_path):
            self.log.error(f"游戏路径不存在：{self.game_path}，使用steam命令启动...")
            self.game_path_exists = False

        try:
            if self.game_path_exists:
                os.startfile(self.game_path)
                self.log.info(f"游戏启动：{self.game_path}")
                return True
            else:
                # 调用系统打开该 URL（会触发 Steam 启动游戏）
                webbrowser.open(self.game_url)
                self.log.info(f"游戏使用steam命令启动")
                return True
        except Exception as e:
            self.log.error(f"启动游戏时发生错误：{e}")
        return False
