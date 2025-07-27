import os
import webbrowser

import pyautogui

from module.config import cfg
from utils.singletonmeta import SingletonMeta


class Game(metaclass=SingletonMeta):
    def __init__(self,logger):
        self.game_path = cfg.game_path
        self.game_url = "steam://rungameid/1973530"
        self.log = logger

    def start_game(self) -> bool:
        """启动游戏"""
        if pyautogui.getWindowsWithTitle(cfg.game_title_name):
            return True

        if not os.path.exists(self.game_path):
            self.log.ERROR(f"游戏路径不存在：{self.game_path}，使用steam命令启动...")
            self.game_path = None

        try:
            if self.game_path:
                os.startfile(self.game_path)
                self.log.INFO(f"游戏启动：{self.game_path}")
                return True
            else:
                # 调用系统打开该 URL（会触发 Steam 启动游戏）
                webbrowser.open(self.game_url)
                self.log.INFO(f"游戏使用steam命令启动")
                return True
        except Exception as e:
            self.log.ERROR(f"启动游戏时发生错误：{e}")
        return False