import random
import socket
import time
import json
from collections import deque
from contextlib import contextmanager
from pathlib import Path

import adbutils
from . import config
from adbutils import AdbError

from module.logger import log

from .utils import is_port_using, str2byte


class MNTInstaller(object):
    """install minitouch for android devices"""

    def __init__(self, device_id):
        self.device_id = device_id
        self.abi = self.get_abi()
        # if self.is_mnt_existed():
        #     log.debug("minitouch 已存在于 {} 中".format(device_id))
        self.install_target_mnt()

    def install_target_mnt(self):
        # subprocess.check_output(
        #     [_ADB, "-s", self.device_id, "shell", "mkdir", "-p", f"{config.MNT_HOME}"]
        # )
        # subprocess.check_output(
        #     [_ADB, "-s", self.device_id, "shell", "mkdir", "-p", f"{config.MNT_HOME}/{self.abi}"]
        # )
        # subprocess.check_output(
        #     [_ADB, "-s", self.device_id, "push", f"{config.MNT_HOME}/{self.abi}/minitouch",
        #      f"{config.MNT_HOME}/{self.abi}/minitouch"]
        # )
        # 检查设备上是否存在minitouch文件
        # 1. 获取设备对象
        device = adbutils.adb.device(serial=self.device_id)

        # 定义远程和本地路径
        remote_path = "/data/local/tmp/minitouch"
        local_path = Path(".") / "assets" / "minitouch" / self.abi / "minitouch"

        # 2. 检查远程文件是否存在
        # adbutils 的 sync.stat 会返回文件信息，如果文件不存在通常大小为0或抛出异常
        needs_push = True
        try:
            remote_file_info = device.sync.stat(remote_path)
            if remote_file_info.size > 0:
                needs_push = False
                log.debug("minitouch已存在，无需再次推送")
        except Exception:
            # 如果发生异常（例如某些版本中文件不存在会报错），则认为需要推送
            needs_push = True

        # 3. 如果需要，执行推送流程
        if needs_push:
            # 检查本地文件是否存在
            if not local_path.exists():
                log.error(f"minitouch 不存在于 {local_path} 中")
                raise FileNotFoundError(f"minitouch not found in {local_path}")

            # 推送文件 (adb push)
            # adbutils 会自动处理流传输
            device.sync.push(local_path, remote_path)

            # 授权 (chmod 777)
            device.shell(["chmod", "777", remote_path])

    def get_abi(self):
        # 1. 获取设备对象
        device = adbutils.adb.device(serial=self.device_id)

        # 2. 直接获取属性 (替代 shell getprop)
        # adbutils 会自动处理命令执行和结果清理
        abi = device.getprop("ro.product.cpu.abi")

        log.debug(f"device {self.device_id} is {abi}")
        return abi

    # def is_mnt_existed(self):
    #     file_list = subprocess.check_output(
    #         [_ADB, "-s", self.device_id, "shell", "ls", f"{config.MNT_HOME}/{self.abi}/minitouch"]
    #     )
    #     return "minitouch" in file_list.decode(config.DEFAULT_CHARSET)


class MNTServer(object):
    """
    manage connection to minitouch using adbutils.
    """

    _PORT_SET = config.PORT_SET

    def __init__(self, device_id):
        self.device_id = device_id

        # 1. 初始化 adbutils 设备对象
        # adbutils 在获取 device 时会自动检查连接，如果断连会抛出异常
        try:
            self.device = adbutils.adb.device(serial=device_id)
        except AdbError:
            raise RuntimeError(f"Device {device_id} not connected")

        log.debug("搜索可用端口 ...")
        self.port = self._get_port()
        log.debug("设备 {} 绑定到端口 {}".format(device_id, self.port))

        # check minitouch (假设 MNTInstaller 内部逻辑也已适配好)
        self.installer = MNTInstaller(device_id)

        # 2. 初始化流对象占位符
        self.mnt_stream = None

        # keep minitouch alive
        self._forward_port()
        self._start_mnt()

        # make sure it's up
        time.sleep(1)
        assert self.heartbeat(), (
            "minitouch did not work. see https://github.com/williamfzc/pyminitouch/issues/11"
        )

    def stop(self):
        """停止服务并清理资源"""
        # 1. 关闭 Shell 流 (相当于 kill 进程)
        if self.mnt_stream:
            try:
                self.mnt_stream.close()
            except Exception as e:
                log.warning(f"关闭 minitouch 流时出错: {e}")
            self.mnt_stream = None

        # 2. 清理端口转发 (新增功能，防止残留)
        try:
            self.device.forward_remove(f"tcp:{self.port}")
        except Exception:
            pass  # 忽略清理失败，可能是连接已断开

        # 3. 回收端口
        self._PORT_SET.add(self.port)
        log.debug("device {} 解除绑定到 {}".format(self.device_id, self.port))

    @classmethod
    def _get_port(cls):
        """get a random port from port set"""
        # 保持原有逻辑不变
        if not cls._PORT_SET:
            raise RuntimeError("No available ports in PORT_SET")
        new_port = random.choice(list(cls._PORT_SET))
        if is_port_using(new_port):
            # 注意：这里应当避免无限递归，实际项目中建议加重试上限
            return cls._get_port()
        cls._PORT_SET.remove(new_port)  # 记得从集合中移除，防止重复分配
        return new_port

    def _forward_port(self):
        """allow pc access minitouch with port"""
        local_address = f"tcp:{self.port}"
        remote_address = "localabstract:minitouch"

        log.debug(f"执行 forward: {local_address} -> {remote_address}")
        # 使用 adbutils 执行 forward
        self.device.forward(local_address, remote_address)
        log.debug("forward 映射设置成功")

    def _start_mnt(self):
        """fork a process to start minitouch on android"""
        cmd = "/data/local/tmp/minitouch"
        log.debug(f"启动 minitouch: {cmd}")

        # 使用 stream=True 启动非阻塞 Shell
        # 这里的 self.mnt_stream 类似于 socket 连接对象
        self.mnt_stream = self.device.shell(cmd, stream=True)

    def heartbeat(self):
        """check if minitouch process (stream) is alive"""
        # 检查流对象是否存在且未关闭
        if self.mnt_stream is None:
            return False

        # adbutils 的 ShellStream 有 closed 属性
        # 如果 socket 连接断开，closed 会变为 True
        return not self.mnt_stream.closed


class MNTConnection(object):
    """manage socket connection between pc and android"""

    _DEFAULT_HOST = config.DEFAULT_HOST
    _DEFAULT_BUFFER_SIZE = config.DEFAULT_BUFFER_SIZE

    def __init__(self, port):
        self.port = port

        # 用于累积和存储来自 minitouch 的 jlog 日志
        self._recv_buffer = ""
        self.jlog_records = deque(maxlen=1000)

        # build connection
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self._DEFAULT_HOST, self.port))
        self.client = client

        # get minitouch server info
        socket_out = client.makefile()

        # v <version>
        # protocol version, usually it is 1. needn't use this
        socket_out.readline()

        # ^ <max-contacts> <max-x> <max-y> <max-pressure>
        _, max_contacts, max_x, max_y, max_pressure, *_ = (
            socket_out.readline().replace("\n", "").replace("\r", "").split(" ")
        )
        self.max_contacts = max_contacts
        self.max_x = max_x
        self.max_y = max_y
        self.max_pressure = max_pressure

        # $ <pid>
        _, pid = socket_out.readline().replace("\n", "").replace("\r", "").split(" ")
        self.pid = pid

        log.debug("在端口上运行的 Minitouch：{}，PID：{}".format(self.port, self.pid))
        log.debug(
            "max_contact: {}; max_x: {}; max_y: {}; max_pressure: {}".format(
                max_contacts, max_x, max_y, max_pressure
            )
        )

    def disconnect(self):
        self.client and self.client.close()
        self.client = None
        log.debug("minitouch disconnected")

    def _parse_jlog_chunk(self, chunk: bytes):
        """
        解析来自 minitouch 的 jlog 日志，返回当前 chunk 中解析出的记录列表。
        """
        records = []
        if not chunk:
            return records

        try:
            text = chunk.decode("utf-8", errors="ignore")
        except Exception:
            return records

        # 处理跨 recv 的半行情况
        text = self._recv_buffer + text
        lines = text.splitlines(keepends=False)

        # 如果最后一行没有换行符，认为是半行，缓存起来等待下一次 recv
        if text and not text.endswith("\n"):
            self._recv_buffer = lines[-1]
            lines = lines[:-1]
        else:
            self._recv_buffer = ""

        for line in lines:
            if not line.startswith("jlog "):
                continue
            payload = line[5:]
            try:
                record = json.loads(payload)
            except Exception:
                continue
            records.append(record)

        return records

    def _drain_logs(self):
        """
        从 socket 中尽可能读取当前可用的所有日志数据，避免缓冲区积压。
        不落盘，仅在 debug 日志中打印条数与首尾 cmd 摘要。
        :return: 本次 drain 得到的 jlog 记录列表，无数据或未连接时返回空列表。
        """
        if not self.client:
            return []

        all_records = []

        prev_timeout = self.client.gettimeout()
        try:
            # 使用一个很小的超时时间，仅拉取当前缓冲区已有的数据
            self.client.settimeout(0.01)
            while True:
                try:
                    chunk = self.client.recv(self._DEFAULT_BUFFER_SIZE)
                except socket.timeout:
                    # 当前没有更多数据
                    break
                if not chunk:
                    # EOF
                    all_records.extend(self._parse_jlog_chunk(chunk))
                    break
                all_records.extend(self._parse_jlog_chunk(chunk))
        finally:
            self.client.settimeout(prev_timeout)

        if not all_records:
            return []

        # 仅打 debug 摘要，不落盘
        try:
            first_cmd = all_records[0].get("cmd")
            last_cmd = all_records[-1].get("cmd")
            log.debug(
                "minitouch jlog drain: count=%d first=%s last=%s",
                len(all_records),
                first_cmd,
                last_cmd,
            )
        except Exception:
            pass

        return all_records

    def send(self, content):
        """发送指令并拉取 minitouch 写回的响应。"""
        byte_content = str2byte(content)
        try:
            self.client.sendall(byte_content)
            log.debug("minitouch send ok, %d bytes", len(byte_content))
        except Exception as e:
            log.error("minitouch send failed: %s", e)
            raise
        # 必须 调用 _drain_logs()
        # minitouch 每处理一条命令会往 socket 写回 ok/jlog。若不读走，
        # 本机 TCP 接收缓冲区会积满，TCP 流控会让 minitouch 在 write 时阻塞，
        # 无法继续 send 我们后续的命令，导致 drag 等操作卡住、无法完成。
        return self._drain_logs()


@contextmanager
def safe_connection(device_id):
    """safe connection runtime to use"""

    # prepare for connection
    server = MNTServer(device_id)
    # real connection
    connection = MNTConnection(server.port)
    try:
        yield connection
    finally:
        # disconnect
        connection.disconnect()
        server.stop()
