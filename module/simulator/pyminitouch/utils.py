import requests
import tempfile
import socket
import subprocess

import module.simulator.pyminitouch.config as config
from module.logger import log


def str2byte(content):
    """ compile str to byte """
    return content.encode(config.DEFAULT_CHARSET)


def download_file(target_url):
    """ download file to temp path, and return its file path for further usage """
    resp = requests.get(target_url)
    with tempfile.NamedTemporaryFile("wb+", delete=False) as f:
        file_name = f.name
        f.write(resp.content)
    return file_name


def is_port_using(port_num):
    """ if port is using by others, return True. else return False """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    try:
        result = s.connect_ex((config.DEFAULT_HOST, port_num))
        # if port is using, return code should be 0. (can be connected)
        return result == 0
    finally:
        s.close()


def restart_adb():
    """ restart adb server """
    import adbutils
    # 1. 停止 ADB 服务 (替代 adb kill-server)
    # 这会向 ADB Server 发送 host:kill 指令
    adbutils.adb.server_kill()

    # 2. 启动 ADB 服务 (替代 adb start-server)
    # adbutils 没有专门的 start_server 方法，
    # 因为当你尝试获取 server 版本或设备列表时，如果服务没启动，它会自动尝试启动。
    # 所以，调用一下 server_version() 是最标准的“唤醒/检查”操作。
    print(f"ADB Server version: {adbutils.adb.server_version()}")


def is_device_connected(device_id):
    """
    使用 adbutils 检查具有给定 serial 的设备是否已连接。

    Args:
        device_id: 设备的 serial 号。

    Returns:
        如果设备已连接并可见，则返回 True，否则返回 False。
    """
    try:
        import adbutils
        # 获取当前所有已连接的设备列表
        devices = adbutils.adb.device_list()

        # 检查 device_id 是否存在于列表中
        # 列表中的每个元素都是一个 Device 对象，可以通过 .serial 属性访问其 ID
        for dev in devices:
            if dev.serial == device_id:
                # 还可以检查设备状态，例如是否为 "device" 状态
                # if dev.serial == device_id and dev.status == "device":
                return True

        # 如果循环结束仍未找到，则设备未连接
        return False

    except Exception as e:
        # 捕获其他可能的异常
        log.error(f"发生意外错误: {e}")
        return False
