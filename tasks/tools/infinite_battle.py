import tkinter as tk
from time import sleep

import win32con
import win32gui

from module.automation import auto
from module.config import cfg
from utils.image_utils import ImageUtils


class InfiniteBattles:
    def __init__(self, root):
        """初始化 InfiniteBattles 类的实例。

        参数:
        - root: tkinter 的根窗口实例。
        """
        self.setup_root(root)
        self.identify_keyword_turn = True
        self.fail_count = 0
        self._set_win()
        self.run()

    def setup_root(self, root):
        """配置根窗口的基本属性和界面元素。

        参数:
        - root: tkinter 的根窗口实例。
        """
        self.root = root
        self.root.title("自动战斗")
        self.root.geometry("500x200")
        self.root.iconbitmap("./assets/logo/my_icon_256X256.ico")

        if cfg.language_in_game == 'zh_cn':
            instruction_text = "\n\n你来到了“都市”，这里是不战斗就无法生存的修罗场\n\n幸好你得到了亚哈神力的相助\n\n“亚哈降神附身代打”获得了\n"
        else:
            instruction_text = "\n\nYou have arrived at the 'The City', a crucible where survival is impossible without combat.\n\nFortunately, you have gained the aid of Ahab's divine power.\n\nEmpowered by Ahab's possession, she will fight for you."
        self.instruction_label = tk.Label(self.root, text=instruction_text)
        self.instruction_label.pack()

    def _ocr_battle(self):
        turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
        turn_ocr_result = auto.find_text_element("turn", turn_bbox)
        if turn_ocr_result is not False:
            auto.mouse_click_blank(move_back=True)
            auto.key_press('p')
            sleep(0.5)
            auto.key_press('enter')
            self.identify_keyword_turn = False

    def _template_battle(self):
        if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
            auto.mouse_click_blank(move_back=True)
            auto.key_press('p')
            sleep(0.5)
            auto.key_press('enter')
            self.fail_count = 0
            return
        else:
            self.fail_count += 1
            sleep(1)

    def _set_win(self):
        from module.game_and_screen import screen
        hwnd = screen.handle
        win32gui.SetWindowPos(
            hwnd._hWnd,  # 目标窗口句柄
            win32con.HWND_NOTOPMOST,  # 关键参数：取消置顶
            0, 0, 0, 0,  # 忽略位置和大小（保持原样）
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE  # 标志位：不移动、不调整大小
        )

    @staticmethod
    def get_z_order_index(hwnd: int) -> int:
        """获取目标窗口在当前顶层窗口中的 Z 顺序索引（0 为最高）"""
        z_order = []

        def enum_callback(hwnd_enum, _):
            # 仅收集可见的顶层窗口（无父窗口）
            if win32gui.IsWindowVisible(hwnd_enum) and win32gui.GetParent(hwnd_enum) == 0:
                z_order.append(hwnd_enum)
            return True

        win32gui.EnumWindows(enum_callback, None)

        try:
            return z_order.index(hwnd)
        except ValueError:
            raise ValueError("目标窗口不是顶层窗口或不可见")

    @staticmethod
    def restore_target_z_order(hwnd: int, target_index: int):
        """将目标窗口恢复到指定的 Z 顺序索引位置"""
        # 获取当前所有可见顶层窗口的 Z 顺序（提升后的状态）
        current_z_order = []

        def enum_callback(hwnd_enum, _):
            if win32gui.IsWindowVisible(hwnd_enum) and win32gui.GetParent(hwnd_enum) == 0:
                current_z_order.append(hwnd_enum)
            return True

        win32gui.EnumWindows(enum_callback, None)

        try:
            current_index = current_z_order.index(hwnd)
        except ValueError:
            print("警告：目标窗口已不在顶层，无需恢复")
            return

        # 若目标窗口已在正确位置，无需操作
        if current_index == target_index:
            return

        # 计算需要插入的位置（目标索引）
        # 插入到目标索引的前一个窗口之后（或 HWND_TOP）
        if target_index == 0:
            insert_after = win32con.HWND_TOP
        else:
            # 目标索引的前一个窗口（需确保有效）
            insert_after = current_z_order[target_index - 1] if (target_index - 1) < len(
                current_z_order) else win32con.HWND_TOP

        # 移动目标窗口到指定位置（不影响其他窗口的相对顺序）
        win32gui.SetWindowPos(
            hwnd,
            insert_after,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        )

    def run(self):
        """开始运行自动战斗。"""
        window = win32gui.FindWindow("UnityWndClass", "LimbusCompany")
        if window:
            original_index = self.get_z_order_index(window)
            win32gui.SetWindowPos(
                window,
                win32con.HWND_TOP,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )
            auto.take_screenshot()
            if auto.find_element("battle/pause_assets.png"):
                self.restore_target_z_order(window, original_index)
                sleep(5)
            else:
                if self.fail_count >= 5 or self.identify_keyword_turn is False:
                    self._ocr_battle()
                else:
                    self._template_battle()

                self.restore_target_z_order(window, original_index)
        else:
            from tasks.base.script_task_scheme import init_game
            init_game()
            self._set_win()

        self.root.after(500, self.run)
