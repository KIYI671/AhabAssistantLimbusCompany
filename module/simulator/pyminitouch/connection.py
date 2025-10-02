import subprocess
import socket
import time
import os
import random
from contextlib import contextmanager
from pathlib import PurePosixPath, Path

import module.simulator.pyminitouch.config as config
from module.logger import log
from module.simulator.pyminitouch.utils import is_device_connected, is_port_using, str2byte

_ADB = config.ADB_EXECUTOR


class MNTInstaller(object):
    """ install minitouch for android devices """

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
        file_list = subprocess.check_output(
            [
                _ADB,
                "-s",
                self.device_id,
                "shell",
                "ls",
                str(PurePosixPath("/data/local/tmp/minitouch").parent),
            ]
        )
        if not PurePosixPath("/data/local/tmp/minitouch").name in file_list.decode(config.DEFAULT_CHARSET):
            raise FileNotFoundError("minitouch 不存在于 {} 中".format(self.device_id))
        mnt_path = Path(".")/ "assets" / "minitouch" / self.abi / "minitouch"
        if not mnt_path.exists():
            raise FileNotFoundError("minitouch not found in {}".format(mnt_path))
        # push and grant
        subprocess.check_call([_ADB, "-s", self.device_id, "push", mnt_path, "/data/local/tmp/minitouch"])
        subprocess.check_call(
            [_ADB, "-s", self.device_id, "shell", "chmod", "777", "/data/local/tmp/minitouch"]
        )




    def get_abi(self):
        abi = subprocess.getoutput(
            "{} -s {} shell getprop ro.product.cpu.abi".format(_ADB, self.device_id)
        )
        log.debug("device {} is {}".format(self.device_id, abi))
        return abi

    # def is_mnt_existed(self):
    #     file_list = subprocess.check_output(
    #         [_ADB, "-s", self.device_id, "shell", "ls", f"{config.MNT_HOME}/{self.abi}/minitouch"]
    #     )
    #     return "minitouch" in file_list.decode(config.DEFAULT_CHARSET)


class MNTServer(object):
    """
    manage connection to minitouch.
    before connection, you should execute minitouch with adb shell.

    command eg::

        adb forward tcp:{some_port} localabstract:minitouch
        adb shell /data/local/tmp/minitouch

    you would better use it via safe_connection ::

        _DEVICE_ID = '123456F'

        with safe_connection(_DEVICE_ID) as conn:
            conn.send('d 0 500 500 50\nc\nd 1 500 600 50\nw 5000\nc\nu 0\nu 1\nc\n')
    """

    _PORT_SET = config.PORT_SET

    def __init__(self, device_id):
        assert is_device_connected(device_id)

        self.device_id = device_id
        log.debug("搜索可用端口 ...")
        self.port = self._get_port()
        log.debug("设备 {} 绑定到端口 {}".format(device_id, self.port))

        # check minitouch
        self.installer = MNTInstaller(device_id)

        # keep minitouch alive
        self._forward_port()
        self.mnt_process = None
        self._start_mnt()

        # make sure it's up
        time.sleep(1)
        assert (
            self.heartbeat()
        ), "minitouch did not work. see https://github.com/williamfzc/pyminitouch/issues/11"

    def stop(self):
        self.mnt_process and self.mnt_process.kill()
        self._PORT_SET.add(self.port)
        log.debug("device {} 解除绑定到 {}".format(self.device_id, self.port))

    @classmethod
    def _get_port(cls):
        """ get a random port from port set """
        new_port = random.choice(list(cls._PORT_SET))
        if is_port_using(new_port):
            return cls._get_port()
        return new_port

    def _forward_port(self):
        """ allow pc access minitouch with port """
        command_list = [
            _ADB,
            "-s",
            self.device_id,
            "forward",
            "tcp:{}".format(self.port),
            "localabstract:minitouch",
        ]
        log.debug("forward 命令：{}".format(" ".join(command_list)))
        output = subprocess.check_output(command_list)
        log.debug("输出： {}".format(output))

    def _start_mnt(self):
        """ fork a process to start minitouch on android """
        command_list = [
            _ADB,
            "-s",
            self.device_id,
            "shell",
            "/data/local/tmp/minitouch",
        ]
        log.debug("启动 minitouch: {}".format(" ".join(command_list)))
        self.mnt_process = subprocess.Popen(command_list, stdout=subprocess.DEVNULL)

    def heartbeat(self):
        """ check if minitouch process alive """
        return self.mnt_process.poll() is None


class MNTConnection(object):
    """ manage socket connection between pc and android """

    _DEFAULT_HOST = config.DEFAULT_HOST
    _DEFAULT_BUFFER_SIZE = config.DEFAULT_BUFFER_SIZE

    def __init__(self, port):
        self.port = port

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

        log.debug(
            "在端口上运行的 Minitouch：{}，PID：{}".format(self.port, self.pid)
        )
        log.debug(
            "max_contact: {}; max_x: {}; max_y: {}; max_pressure: {}".format(
                max_contacts, max_x, max_y, max_pressure
            )
        )

    def disconnect(self):
        self.client and self.client.close()
        self.client = None
        log.debug("minitouch disconnected")

    def send(self, content):
        """ send message and get its response """
        byte_content = str2byte(content)
        self.client.sendall(byte_content)
        return self.client.recv(self._DEFAULT_BUFFER_SIZE)


@contextmanager
def safe_connection(device_id):
    """ safe connection runtime to use """

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
