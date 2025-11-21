import random
import re
import subprocess
from time import sleep, time

import cv2
import numpy as np
from adbutils import adb

from module.config import cfg
from module.logger import log
from module.simulator import insert_swipe
from module.simulator.pyminitouch import MNTDevice
from utils.singletonmeta import SingletonMeta

key_list = {
    'a': 29, 'b': 30, 'c': 31, 'd': 32, 'e': 33,
    'f': 34, 'g': 35, 'h': 36, 'i': 37, 'j': 38,
    'k': 39, 'l': 40, 'm': 41, 'n': 42, 'o': 43,
    'p': 44, 'q': 45, 'r': 46, 's': 47, 't': 48,
    'u': 49, 'v': 50, 'w': 51, 'x': 52, 'y': 53,
    'z': 54,
    '0': 7, '1': 8, '2': 9, '3': 10, '4': 11,
    '5': 12, '6': 13, '7': 14, '8': 15, '9': 16,
    'enter': 66,
    'esc': 111,
    'space': 62,
    'tab': 61,
    'shift': 59,
    'ctrl': 113,
    'alt': 57,
}


class SimulatorControl:
    connection_device = None

    @staticmethod
    def clean_connect():
        if SimulatorControl.connection_device is None:
            return
        SimulatorControl.connection_device.simulator_control.stop()
        SimulatorControl.connection_device.adb_disconnect()
        SimulatorControl.connection_device = None

    def __init__(self) -> None:
        self.is_pause = False
        self.restore_time = None
        self.simulator_device = None
        # self.simulator_control = None
        self.simulator_max_x = None
        self.simulator_port = None

        self.game_package_name = 'com.ProjectMoon.LimbusCompany'

        self.get_simulator()

    def start_game(self):
        if self.simulator_device is None:
            self.get_simulator()
        self.simulator_device.app_start(self.game_package_name)

    def adb_connect(self):
        # Try to connect
        for _ in range(3):
            self.simulator_port = f"127.0.0.1:{int(cfg.simulator_port)}"
            msg = adb.connect(self.simulator_port)
            # Connected to 127.0.0.1:59865
            # Already connected to 127.0.0.1:59865
            if 'connected' in msg:
                log.debug(f"成功连接至:{self.simulator_port},连接信息: {msg}")
                break
            # bad port number '598265' in '127.0.0.1:598265'
            elif 'bad port' in msg:
                log.error(f'连接失败，端口号{self.simulator_port}不正确，可能是拼写错误或不规范')

    def adb_disconnect(self):
        try:
            for _ in range(3):
                msg = adb.disconnect(self.simulator_port)
                # Connected to 127.0.0.1:59865
                # Already connected to 127.0.0.1:59865
                if 'disconnected' in msg:
                    log.debug(f"成功断开连接于:{self.simulator_port},连接信息: {msg}")
                    break
                # bad port number '598265' in '127.0.0.1:598265'
                elif 'bad port' in msg:
                    log.error(f'断开连接失败，端口号{self.simulator_port}不正确，可能是拼写错误或不规范')
        except:
            pass

    def get_simulator(self):
        if self.simulator_device is not None:
            return self.simulator_device

        if self.simulator_port is None:
            self.adb_connect()

        self.simulator_device = adb.device(self.simulator_port)

        # 提取目标设备的序列号
        target_serial = self.simulator_device.serial

        # 通过序列号获取设备对象
        self.simulator_control = MNTDevice(target_serial)

        # 提取分辨率（如 1080x1920）
        size_output = self.simulator_device.shell(["wm", "size"])
        match = re.search(r"(\d+)x(\d+)", size_output)
        if match:
            height = int(match.group(1))  # X: 宽度
            self.simulator_max_x = height

        SimulatorControl.connection_device = self

        log.debug(f"连接成功，已将模拟器实例记录至SimulatorControl.connection_device")

        return self.simulator_device

    def screenshot(self):
        data = self.simulator_device.shell(['screencap', '-p'], stream=False, encoding=None)
        if len(data) < 500:
            log.warning(f'意外截图: {data}')
        image = np.frombuffer(data, np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        return image

    def set_pause(self) -> None:
        """
        设置暂停状态
        """
        self.is_pause = not self.is_pause  # 设置暂停状态
        if self.is_pause:
            msg = "操作将在下一次点击时暂停"
        else:
            msg = "继续操作"
        log.info(msg)

    def wait_pause(self) -> None:
        """
        当处于暂停状态时堵塞的进行等待
        """
        pause_identity = False
        while self.is_pause:
            if not pause_identity is False:
                log.info("AALC 已暂停")
                pause_identity = True
            sleep(1)
            self.restore_time = time()

    def mouse_click(self, x, y, times=1) -> bool:
        """在指定坐标上执行点击操作

        Args:
            x (int): x坐标
            y (int): y坐标
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """
        if self.simulator_device is None:
            self.get_simulator()

        pos_x, pos_y = self._scale(x, y)

        msg = f"点击位置:({x},{y})"
        log.debug(msg)
        for i in range(times):
            self.simulator_device.shell(f'input tap {x} {y}')
            # 多次点击执行很快所以暂停放到循环外

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y) -> None:
        """鼠标从指定位置向下拖动

        Args:
            x (int): x坐标
            y (int): y坐标
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        if self.simulator_device is None:
            self.get_simulator()

        scale = cfg.set_win_size / 1080
        self.mouse_drag(x, y, 0.4, 0, int(300) * scale)

        msg = f"选择卡包:({x},{y})"
        log.debug(msg)

    def mouse_scroll(self, direction: int = -3) -> bool:
        """占位"""
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1) -> bool:
        """在空白位置点击鼠标
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """

        msg = "点击（1，1）空白位置"
        log.debug(msg)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        for i in range(times):
            self.mouse_click(x, y)

        self.wait_pause()
        return True

    def mouse_to_blank(self, coordinate=(1, 1)) -> None:  # background未重载
        """占位"""
        return

    def key_press(self, key: str):
        """模拟键盘输入文本
        Args:
            key (str): 按键名称
        """
        if self.simulator_device is None:
            self.get_simulator()
        try:
            cmd = f"input keyevent {key_list[key]}"
            self.simulator_device.shell(cmd)
        except Exception as e:
            log.error(f"输入失败：{e}")

    def _scale(self, x, y):
        pos_x = self.simulator_max_x - y
        pos_y = x
        if pos_x <= 0:
            pos_x = 1
        return pos_x, pos_y

    def clear_mnt(self):
        self.simulator_control.stop()

    def mouse_drag(self, x, y, drag_time=0.2, dx=0, dy=0) -> None:
        """鼠标从指定位置拖动到另一个位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            drag_time (float): 拖动时间
            dx (int): x方向拖动距离
            dy (int): y方向拖动距离
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        if self.simulator_device is None:
            self.get_simulator()

        pos_x, pos_y = self._scale(x, y)
        pos_x_2, pos_y_2 = self._scale(x + dx, y + dy)

        self.simulator_control.ext_smooth_swipe(
            [(pos_x, pos_y), (pos_x_2, pos_y_2)], duration=drag_time * 1000 / 10, part=50, no_up=True
        )
        if drag_time * 0.3 > 0.5:
            sleep(drag_time * 0.3)
        else:
            sleep(0.5)
        self.simulator_control.swipe([(pos_x_2, pos_y_2), (pos_x_2, pos_y_2)], duration=drag_time * 1000 / 10,
                                     no_down=True)

    def close_current_app(self):
        if self.simulator_device is None:
            self.get_simulator()
        self.simulator_device.app_stop(self.game_package_name)

    def check_game_alive(self) -> bool:
        """检查游戏是否存活
        Returns:
            bool: True表示游戏存活，False表示游戏未启动或已退出
        """
        package = self.simulator_device.app_current().package
        if package != self.game_package_name:
            return False
        return True

    def mouse_drag_link(self, position: list, drag_time=0.15) -> None:
        """
        拖动鼠标经过多个中间点（折线），最后松开
        """
        if self.simulator_device is None:
            self.get_simulator()
        msg = f"开始拉链，列表{position}"
        log.debug(msg)

        position_conversion = []
        for pos in position:
            position_conversion.append((self.simulator_max_x - pos[1], pos[0]))

        self.simulator_control.swipe(position_conversion, duration=drag_time * 1000)
