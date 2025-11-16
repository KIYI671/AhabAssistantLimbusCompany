import asyncio
import ctypes
import json
import os
import subprocess
import re
import sys
import time
from functools import partial
from time import sleep

import cv2
import numpy as np
from adbutils import adb, AdbError
from utils.utils import run_as_user
from module.config import cfg
from module.logger import log
from module.simulator import insert_swipe

usual_key_code = {
    'q': 16, 'w': 17, 'e': 18, 'r': 19, 't': 20, 'y': 21, 'u': 22, 'i': 23, 'o': 24, 'p': 25,
    'a': 30, 's': 31, 'd': 32, 'f': 33, 'g': 34, 'h': 35, 'j': 36, 'k': 37, 'l': 38,
    'z': 44, 'x': 45, 'c': 46, 'v': 47, 'b': 48, 'n': 49, 'm': 50,
    '1': 2, '2': 3, '3': 4, '4': 5, '5': 6,
    '6': 7, '7': 8, '8': 9, '9': 10, '0': 11,
    'enter': 28,
    'esc': 1,
    'space': 57,
    'tab': 15,
    'shift': 42,
    'ctrl': 29,
    'alt': 56,
}


class NemuIpcIncompatible(Exception):
    pass


class NemuIpcError(Exception):
    pass


class CaptureStd:
    """
    Capture stdout and stderr from both python and C library
    https://stackoverflow.com/questions/5081657/how-do-i-prevent-a-c-shared-library-to-print-on-stdout-in-python/17954769

    ```
    with CaptureStd() as capture:
        # String wasn't printed
        print('whatever')
    # But captured in ``capture.stdout``
    print(f'Got stdout: "{capture.stdout}"')
    print(f'Got stderr: "{capture.stderr}"')
    ```
    """

    def __init__(self):
        self.stdout = b''
        self.stderr = b''

    def _redirect_stdout(self, to):
        sys.stdout.close()
        os.dup2(to, self.fdout)
        sys.stdout = os.fdopen(self.fdout, 'w')

    def _redirect_stderr(self, to):
        sys.stderr.close()
        os.dup2(to, self.fderr)
        sys.stderr = os.fdopen(self.fderr, 'w')

    def __enter__(self):
        self.fdout = sys.stdout.fileno()
        self.fderr = sys.stderr.fileno()
        self.reader_out, self.writer_out = os.pipe()
        self.reader_err, self.writer_err = os.pipe()
        self.old_stdout = os.dup(self.fdout)
        self.old_stderr = os.dup(self.fderr)

        file_out = os.fdopen(self.writer_out, 'w')
        file_err = os.fdopen(self.writer_err, 'w')
        self._redirect_stdout(to=file_out.fileno())
        self._redirect_stderr(to=file_err.fileno())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._redirect_stdout(to=self.old_stdout)
        self._redirect_stderr(to=self.old_stderr)
        os.close(self.old_stdout)
        os.close(self.old_stderr)

        self.stdout = self.recvall(self.reader_out)
        self.stderr = self.recvall(self.reader_err)
        os.close(self.reader_out)
        os.close(self.reader_err)

    @staticmethod
    def recvall(reader, length=1024) -> bytes:
        fragments = []
        while 1:
            chunk = os.read(reader, length)
            if chunk:
                fragments.append(chunk)
            else:
                break
        output = b''.join(fragments)
        return output


class CaptureNemuIpc(CaptureStd):
    instance = None

    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    def is_capturing(self):
        """
        Only capture at the topmost wrapper to avoid nested capturing
        If a capture is ongoing, this instance does nothing
        """
        cls = self.__class__
        return isinstance(cls.instance, cls) and cls.instance != self

    def __enter__(self):
        if self.is_capturing():
            return self
        super().__enter__()
        CaptureNemuIpc.instance = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_capturing():
            return

        CaptureNemuIpc.instance = None
        super().__exit__(exc_type, exc_val, exc_tb)

        self.check_stdout()
        self.check_stderr()

    def check_stdout(self):
        if not self.stdout:
            return
        self.logger.info(f'NemuIpc stdout: {self.stdout}')

    def check_stderr(self):
        if not self.stderr:
            return
        self.logger.error(f'NemuIpc stderr: {self.stderr}')

        # Calling an old MuMu12 player
        # Tested on 3.4.0
        # b'nemu_capture_display rpc error: 1783\r\n'
        # Tested on 3.7.3
        # b'nemu_capture_display rpc error: 1745\r\n'
        if b'error: 1783' in self.stderr or b'error: 1745' in self.stderr:
            raise NemuIpcIncompatible(
                f'NemuIpc requires MuMu12 version >= 3.8.13, please check your version')
        # contact_id incorrect
        # b'nemu_capture_display cannot find rpc connection\r\n'
        if b'cannot find rpc connection' in self.stderr:
            raise NemuIpcError(self.stderr)
        # Emulator died
        # b'nemu_capture_display rpc error: 1722\r\n'
        # MuMuVMMSVC.exe died
        # b'nemu_capture_display rpc error: 1726\r\n'
        # No idea how to handle yet
        if b'error: 1722' in self.stderr or b'error: 1726' in self.stderr:
            raise NemuIpcError('Emulator instance is probably dead')


class MumuControl:
    connection_device = None

    @staticmethod
    def clean_connect():
        if MumuControl.connection_device is None:
            return
        MumuControl.connection_device.disconnect()
        MumuControl.connection_device.adb_disconnect()
        MumuControl.connection_device = None

    def __init__(self, instance_number=0, display_id=0):
        self.install_path = None
        self.nemu_folder = None
        self.mumu_version = None
        self.exe_path = None
        self.multi_instance_number = instance_number
        self.port = None
        self.device = None

        self.lib = None
        self._ev = asyncio.new_event_loop()
        self.display_id = display_id

        self.connect_id: int = 0
        self.width = 0
        self.height = 0

        self.game_package_name = 'com.ProjectMoon.LimbusCompany'

        self.is_pause = False
        self.restore_time = None

        self.start()
        self.adb_connect()

    def adb_connect(self):
        # Try to connect
        for _ in range(3):
            port = self.get_mumu_adb_port()
            msg = adb.connect(port)
            # Connected to 127.0.0.1:59865
            # Already connected to 127.0.0.1:59865
            if 'connected' in msg:
                log.debug(f"成功连接至:{port},连接信息: {msg}")
                break
            # bad port number '598265' in '127.0.0.1:598265'
            elif 'bad port' in msg:
                log.error(f'连接失败，端口号{port}不正确，可能是拼写错误或不规范')

    def adb_disconnect(self):
        try:
            for _ in range(3):
                port = self.get_mumu_adb_port()
                msg = adb.disconnect(port)
                # Connected to 127.0.0.1:59865
                # Already connected to 127.0.0.1:59865
                if 'disconnected' in msg:
                    log.debug(f"成功断开连接于:{port},连接信息: {msg}")
                    break
                # bad port number '598265' in '127.0.0.1:598265'
                elif 'bad port' in msg:
                    log.error(f'断开连接失败，端口号{port}不正确，可能是拼写错误或不规范')
        except:
            pass

    def start_game(self):
        if self.device is None:
            self.device = adb.device(self.get_mumu_adb_port())
        try:
            self.device.app_start(self.game_package_name)
        except:
            log.error(f'启动游戏失败，请确认是否安装了Limbus Company')
            sleep(10)
            self.start_game()

    def mumu_control_api_backend(self):
        if os.name == 'nt':
            try:
                import winreg
                # 读取注册表中的键值
                software_name = ["MuMuPlayer-12.0", "MuMuPlayer", "MuMuPlayerGlobal-12.0", "MuMuPlayerGlobal",
                                 "YXArkNights-12.0"]
                key = None
                for name in software_name:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                             rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{name}")
                    except:
                        continue
                if not key:
                    return None
                self.install_path = os.path.dirname(winreg.QueryValueEx(key, "DisplayIcon")[0]).strip('"')
                mumu_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
                winreg.CloseKey(key)
            except:
                log.error(f"读取注册表失败，无法获取MuMu安装路径，也可能是未安装MuMu模拟器，或使用了某种特供版本",
                          exc_info=True)
                return None
            # 修改路径，使其指向MuMuManager.exe
            self.exe_path = os.path.join(self.install_path, "MuMuManager.exe")
            if not os.path.isfile(self.exe_path):
                from pathlib import Path
                exe_path = Path(self.exe_path)
                # 1. 拆分路径为各个组成部分
                parts = list(exe_path.parts)
                # 2. 修改倒数第二个部分为 "shell"（确保路径长度足够，避免越界）
                if len(parts) >= 2:
                    parts[-2] = "shell"
                # 3. 重新拼接成新路径
                new_exe_path = Path(*parts)  # 用 * 解包列表为Path的参数
                # 转换为字符串（可选，若需要字符串路径）
                new_exe_path_str = str(new_exe_path)
                self.exe_path = new_exe_path_str
                if not os.path.isfile(self.exe_path):
                    log.error(f"查找MuMuManager.exe失败，路径不存在，请检查MuMu模拟器是否安装或是否为特供版本")
                    return None

            def detect_major_version():
                match = re.match(r'^(\d+)\.', mumu_version)
                if match:
                    return int(match.group(1))

            self.mumu_version = detect_major_version()

    def get_mumu_adb_port(self, multi_instance_number=None):
        try:
            if multi_instance_number is None and self.multi_instance_number is None:
                self.multi_instance_number = 0
            if int(self.multi_instance_number) <= 1536:
                cmd = f'{self.exe_path} adb -v {self.multi_instance_number}'
                proc = subprocess.run(cmd, universal_newlines=True, capture_output=True, encoding="utf-8")
                adb_info = json.loads(proc.stdout)
                try:
                    return f"{adb_info['adb_host']}:{adb_info['adb_port']}"
                except:
                    return f"127.0.0.1:{int(self.multi_instance_number) * 32 + 16384}"
        except:
            self.start()
            self.get_mumu_adb_port(self.multi_instance_number)

    def start(self):
        try:
            log.debug(f"开始启动MUMU模拟器实例编号{self.multi_instance_number}")
            keptlive = self.get_app_keptlive()
            if keptlive:
                log.info(f"检测到启用了应用后台保活功能，即将关闭")
                if self.get_launch_status() == 'start_finished':
                    log.info(f"检测到模拟器处于启用状态，为关闭应用后台保活，需执行重启")
                    self.stop()
                self.disable_app_keptlive()
            else:
                log.debug(f"未启用应用后台保活功能,可正常运行")
            # 使用mumumanager控制模拟器开启与关闭
            command = [self.exe_path, "control", "-v", str(self.multi_instance_number), "launch"]
            run_as_user(command)
            # 等待模拟器启动完成
            for _ in range(cfg.start_emulator_timeout):
                time.sleep(1)
                if self.get_launch_status() == 'start_finished':
                    break
            self.port = self.get_mumu_adb_port()
            self.load_dll()
            log.debug(f"MUMU模拟器编号{self.multi_instance_number}启动完成")
            self.connect()
        except:
            self.mumu_control_api_backend()
            self.start()

    def stop(self):
        try:
            command = [self.exe_path, "control", "-v", str(self.multi_instance_number), "shutdown"]
            subprocess.run(command)
            log.debug(f"MUMU模拟器编号{self.multi_instance_number}关闭完成")
        except:
            self.mumu_control_api_backend()
            self.stop()

    def get_path(self):
        # 获取MuMuManager.exe所在的目录
        return self.install_path

    def get_device_path(self):
        # 获取MuMuNxDevice.exe所在的目录
        try:
            if self.mumu_version == 5:
                return os.path.join(os.path.dirname(self.install_path), "nx_device", "12.0", "shell")
            else:
                return self.install_path
        except:
            self.mumu_control_api_backend()
            self.get_device_path()

    def get_manager_path(self):
        # 获取MuMuManager.exe所在的路径
        return self.exe_path

    def get_nemu_client_path(self):
        # 获取external_renderer_ipc.dll所在的路径
        try:
            if self.mumu_version == 5:
                return os.path.join(os.path.dirname(self.install_path), "nx_device", "12.0", "shell", "sdk",
                                    "external_renderer_ipc.dll")
            else:
                return os.path.join(self.install_path, "sdk", "external_renderer_ipc.dll")
        except:
            self.mumu_control_api_backend()
            self.get_nemu_client_path()

    def get_app_keptlive(self):
        # 获取应用保活状态
        try:
            log.debug(f"开始获取应用保活状态")
            command = f""" "{self.exe_path}" setting -v {self.multi_instance_number} -k app_keptlive"""
            proc = subprocess.run(
                command,
                shell=True,
                universal_newlines=True,
                capture_output=True,
                check=True  # 新增：如果命令返回非零状态码则抛出异常
            )

            # 检查输出是否为空
            if not proc.stdout.strip():
                raise ValueError("命令返回空输出")

            # 尝试解析JSON
            try:
                proc_result = json.loads(proc.stdout.strip())
                result = bool(proc_result.get("app_keptlive") == "true")  # 使用get避免KeyError
                return result
            except json.JSONDecodeError as json_err:
                log.error(f"JSON解析失败！原始输出: {proc.stdout}")
                raise  # 重新抛出异常或处理

        except subprocess.CalledProcessError as cmd_err:
            log.error(f"命令执行失败！返回码: {cmd_err.returncode}, 错误输出: {cmd_err.stderr}")
            # 可选：根据业务需求返回默认值或重新抛出
            return False
        except Exception as e:
            log.error(f"获取应用保活状态失败：{e}", exc_info=True)  # 记录完整堆栈
            self.mumu_control_api_backend()
            return self.get_app_keptlive()

    def disable_app_keptlive(self):
        # 关闭后台保活
        try:
            command = f""" "{self.exe_path}" setting -v {self.multi_instance_number} -k app_keptlive -val false"""
            subprocess.run(command, shell=True, universal_newlines=True, capture_output=True)
        except:
            self.mumu_control_api_backend()
            self.disable_app_keptlive()

    def enable_app_keptlive(self):
        # 开启保活
        try:
            command = f""" "{self.exe_path}" setting -v {self.multi_instance_number} -k app_keptlive -val true"""
            subprocess.run(command, universal_newlines=True, capture_output=True)
        except:
            self.mumu_control_api_backend()
            self.enable_app_keptlive()

    def get_launch_status(self):
        # 获取启动状态
        cmd = [self.exe_path, "info", "-v", str(self.multi_instance_number)]
        proc = subprocess.run(cmd, universal_newlines=True, capture_output=True, encoding="utf-8")
        info = json.loads(proc.stdout)
        try:
            return info["player_state"]
        except:
            return "not_launched"

    def load_dll(self):
        nemu_folder = os.path.dirname(self.install_path)
        list_dll = [
            # MuMuPlayer12
            os.path.abspath(os.path.join(nemu_folder, './shell/sdk/external_renderer_ipc.dll')),
            # MuMuPlayer12 5.0
            os.path.abspath(os.path.join(nemu_folder, './nx_device/12.0/shell/sdk/external_renderer_ipc.dll')),
        ]
        ipc_dll = ''
        for ipc_dll in list_dll:
            if not os.path.exists(ipc_dll):
                continue
            try:
                self.lib = ctypes.CDLL(ipc_dll)
                break
            except OSError as e:
                log.error(e.__str__())
                log.error(f'ipc_dll={ipc_dll} 存在, 但无法加载')
                continue
        if not self.lib:
            log.error("NemuIpc 需要 MuMu12 版本 >= 3.8.13，请检查您的版本。")
            log.error(f'以下路径均不存在')
            for path in list_dll:
                log.error(f'{path}')
            raise NemuIpcIncompatible("请在AALC设置中检查您的MuMu播放器12版本和安装路径。")
        else:
            log.debug(f"ipc_dll={ipc_dll} 加载成功")

    def connect(self):
        if self.connect_id > 0:
            return

        self.nemu_folder = os.path.dirname(self.install_path)

        connect_id = self.ev_run_sync(
            self.lib.nemu_connect,
            self.nemu_folder, self.multi_instance_number
        )
        if connect_id == 0:
            raise NemuIpcError(
                '连接失败，请检查nemu_folder是否正确，模拟器是否正在运行'
            )

        self.connect_id = connect_id

        MumuControl.connection_device = self

        log.debug(f"连接成功，已将模拟器实例记录至MumuControl.connection_device")

    def disconnect(self):
        if self.connect_id == 0:
            return

        self.ev_run_sync(
            self.lib.nemu_disconnect,
            self.connect_id
        )

        log.debug(f'NemuIpc 断开连接: {self.connect_id}')
        self.connect_id = 0

    def reconnect(self):
        self.disconnect()
        self.connect()

    async def ev_run_async(self, func, *args, timeout=1, **kwargs):
        """
        Args:
            func: Sync function to call
            *args:
            timeout:
            **kwargs:

        Raises:
            asyncio.TimeoutError: If function call timeout
        """
        func_wrapped = partial(func, *args, **kwargs)
        # Increased timeout for slow PCs
        # Default screenshot interval is 0.2s, so a 0.15s timeout would have a fast retry without extra time costs
        result = await asyncio.wait_for(self._ev.run_in_executor(None, func_wrapped), timeout=timeout)
        return result

    def ev_run_sync(self, func, *args, **kwargs):
        """
        Args:
            func: Sync function to call
            *args:
            **kwargs:

        Raises:
            asyncio.TimeoutError: If function call timeout
            NemuIpcIncompatible:
            NemuIpcError
        """
        result = self._ev.run_until_complete(self.ev_run_async(func, *args, **kwargs))

        err = False
        if func.__name__ == 'nemu_connect':
            if result == 0:
                err = True
        else:
            if result > 0:
                err = True
        # Get to actual error message printed in std
        if err:
            log.warning(f'调用 {func.__name__} 失败，结果={result}')
            with CaptureNemuIpc(log):
                result = self._ev.run_until_complete(self.ev_run_async(func, *args, **kwargs))

        return result

    def get_resolution(self):
        """
        Get emulator resolution, `self.width` and `self.height` will be set
        """
        if self.connect_id == 0:
            self.connect()

        width_ptr = ctypes.pointer(ctypes.c_int(0))
        height_ptr = ctypes.pointer(ctypes.c_int(0))
        nullptr = ctypes.POINTER(ctypes.c_int)()

        ret = self.ev_run_sync(
            self.lib.nemu_capture_display,
            self.connect_id, self.display_id, 0, width_ptr, height_ptr, nullptr
        )
        if ret > 0:
            raise NemuIpcError('nemu_capture_display在get_resolution（）期间失败')
        self.width = width_ptr.contents.value
        self.height = height_ptr.contents.value
        log.debug(f'获取到模拟器分辨率: {self.width} x {self.height}')
        if int(cfg.set_win_size) != int(self.height):
            if self.height in (720, 900, 1080, 1440, 1800, 2160):
                cfg.set_value('set_win_size', self.height)
                from module.automation import auto
                auto.clear_img_cache()
                log.debug(f'自动将AALC识别的分辨率适配模拟器设置: {self.width} x {self.height}')

    def screenshot(self, timeout=0.15):
        """
        Returns:
            np.ndarray: Image array in RGBA color space
                Note that image is upside down
        """
        if self.connect_id == 0:
            self.connect()

        if self.height == 0:
            self.get_resolution()

        width_ptr = ctypes.pointer(ctypes.c_int(self.width))
        height_ptr = ctypes.pointer(ctypes.c_int(self.height))
        length = self.width * self.height * 4
        pixels_pointer = ctypes.pointer((ctypes.c_ubyte * length)())

        ret = self.ev_run_sync(
            self.lib.nemu_capture_display,
            self.connect_id, self.display_id, length, width_ptr, height_ptr, pixels_pointer,
            timeout=timeout,
        )
        if ret > 0:
            raise NemuIpcError('nemu_capture_display failed during screenshot()')

        # image = np.ctypeslib.as_array(pixels_pointer, shape=(self.height, self.width, 4))
        image = np.ctypeslib.as_array(pixels_pointer.contents).reshape((self.height, self.width, 4))
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        cv2.flip(image, 0, dst=image)
        return image

    def down(self, x, y):
        """
        Contact down, continuous contact down will be considered as swipe
        """
        if self.connect_id == 0:
            self.connect()
        if self.height == 0:
            self.get_resolution()

        x = int(x)
        y = int(y)

        ret = self.ev_run_sync(
            self.lib.nemu_input_event_touch_down,
            self.connect_id, self.display_id, x, y
        )
        if ret > 0:
            raise NemuIpcError('nemu_input_event_touch_down failed')

    def up(self):
        """
        Contact up
        """
        if self.connect_id == 0:
            self.connect()

        ret = self.ev_run_sync(
            self.lib.nemu_input_event_touch_up,
            self.connect_id, self.display_id
        )
        if ret > 0:
            raise NemuIpcError('nemu_input_event_touch_up failed')

    def key_down(self, key_code):
        if self.connect_id == 0:
            self.connect()

        ret = self.ev_run_sync(
            self.lib.nemu_input_event_key_down,
            self.connect_id, self.display_id, key_code
        )
        if ret > 0:
            raise NemuIpcError('nemu_input_event_key_down failed')

    def key_up(self, key_code):
        if self.connect_id == 0:
            self.connect()

        ret = self.ev_run_sync(
            self.lib.nemu_input_event_key_up,
            self.connect_id, self.display_id, key_code
        )
        if ret > 0:
            raise NemuIpcError('nemu_input_event_key_up failed')

    def key_press(self, key):
        self.key_down(usual_key_code[key])
        time.sleep(0.015)
        self.key_up(usual_key_code[key])

    def click(self, x, y):
        self.down(x, y)
        time.sleep(0.015)
        self.up()
        time.sleep(0.035)

    def swipe(self, x1, y1, x2, y2, duration, min_distance=10):
        points = insert_swipe(p0=(x1, y1), p3=(x2, y2), min_distance=min_distance)

        for point in points:
            self.down(*point)
            time.sleep(duration / min_distance)

        time.sleep(0.2)
        self.up()
        time.sleep(0.050)

    def long_click(self, x, y, duration):
        self.down(x, y)
        time.sleep(duration)
        self.up()
        time.sleep(0.050)

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
            time.sleep(1)
            self.restore_time = time.time()

    def mouse_click(self, x, y, times=1, move_back=False) -> bool:
        """在指定坐标上执行点击操作

        Args:
            x (int): x坐标
            y (int): y坐标
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """
        for _ in range(times):
            self.click(x, y)

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y, move_back=True) -> None:
        """鼠标从指定位置向下拖动

        Args:
            x (int): x坐标
            y (int): y坐标
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        scale = cfg.set_win_size / 1080
        x2 = x
        y2 = y + int(300 * scale)
        self.swipe(x1=x, y1=y, x2=x2, y2=y2, duration=0.4)

        msg = f"选择卡包:({x},{y})"
        log.debug(msg, stacklevel=2)

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True) -> None:
        """鼠标从指定位置拖动到另一个位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            drag_time (float): 拖动时间
            dx (int): x方向拖动距离
            dy (int): y方向拖动距离
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        self.down(x, y)
        x2 = x + dx
        y2 = y + dy
        points = insert_swipe(p0=(x, y), p3=(x2, y2))

        for point in points:
            self.down(*point)
            time.sleep(0.020)

        if drag_time * 0.3 > 0.5:
            time.sleep(drag_time * 0.3)
        else:
            time.sleep(0.5)

        self.up()

    def mouse_scroll(self, direction: int = -3) -> bool:
        """占位"""
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False) -> bool:
        self.mouse_click(coordinate[0], coordinate[1], times, move_back)
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        """占位"""
        return

    def mouse_move(self, coordinate=(1, 1)) -> None:
        """占位"""
        return

    def get_mouse_position(self) -> tuple[int, int]:
        """占位"""
        return 0, 0

    def mouse_drag_link(self, position: list, drag_time=0.25, min_distance=10) -> None:
        """鼠标从指定位置拖动到指定位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            position (list): 目标位置列表
            drag_time (float): 拖动时间
        """
        self.down(position[0][0], position[0][1])
        p = (position[0][0], position[0][1])
        for pos in position[1:]:
            points = insert_swipe(p0=(p[0], p[1]), p3=(pos[0], pos[1]), min_distance=min_distance)

            for point in points:
                self.down(*point)
                time.sleep(drag_time / min_distance)

            p = pos

        time.sleep(0.5)
        self.up()
        time.sleep(0.050)

    def check_game_alive(self) -> bool:
        """检查游戏是否存活
        Returns:
            bool: True表示游戏存活，False表示游戏未启动或已退出
        """
        package = self.get_current_package()
        if package != self.game_package_name:
            return False
        return True

    def get_current_package(self):
        for _ in range(3):
            try:
                current_package = self.device.app_current().package
                log.debug(f"当前应用包名: {current_package}")
                return current_package
            except AdbError as e:
                log.error(f"获取当前应用包名错误: {e}")
                continue
        return ""

    def close_current_app(self):
        log.info("Close Current App")
        if self.get_current_package() is None:
            return
        self.device.app_stop(self.get_current_package())

#
# if __name__ == "__main__":
#     # mumu = MumuControl()
#     # mumu.start()
#     # mumu.click(1400,550)
#     mumu = MumuControl(instance_number=1)
#     mumu.start()
#     print(adb.list())
#     adb_port = mumu.get_mumu_adb_port()
#     mumu.adb_connect()
#     print(mumu.get_launch_status())
#     #
#     #
#     #
#     # d = adb.device(adb_port)
#     #
#     # print(d.app_current().package)
#
#     print(adb.list())
