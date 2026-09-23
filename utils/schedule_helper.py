"""
utils.schedule_helper: 计划任务的帮助类的实现

- Windows: 任务计划程序 (Schedule.Service COM)
- Linux: systemd 用户定时器（每日任务）+ XDG autostart（登录自启动）
"""

import datetime
import getpass
import os
import re
import subprocess
import sys

from module.logger import log
from module.platform_compat import IS_LINUX, IS_WINDOWS

_SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
_AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")


class ScheduleHelper:
    """
    计划任务的帮助类
    """

    def __init__(self):
        if IS_WINDOWS:
            self._impl = ScheduleHelper_Win32()
        elif IS_LINUX:
            self._impl = ScheduleHelper_Linux()
        else:
            raise RuntimeError("未知平台")

    def register_daily_task(self, task_name: str, cmd_line: str, h: int, m: int):
        """
        注册每日任务

        :param task_name: 任务名称
        :type task_name: str
        :param cmd_line: 命令行
        :type cmd_line: str
        :param h: 时
        :type h: int
        :param m: 分
        :type m: int
        """
        if (h not in range(24)) or (m not in range(60)):
            raise ValueError("无效参数")
        self._impl.register_daily_task(task_name, cmd_line, h, m)

    def register_onstart_task(self, task_name: str, cmd_line: str):
        """
        注册启动任务

        :param task_name: 任务名称
        :type task_name: str
        :param cmd_line: 命令行
        :type cmd_line: str
        """
        self._impl.register_onstart_task(task_name, cmd_line)

    def unregister_task(self, task_name: str):
        """
        注销任务

        :param task_name: 任务名称
        :type task_name: str
        """
        self._impl.unregister_task(task_name)
        log.info("移除每日任务成功")


def _app_command_args(cmd_line: str) -> list[str]:
    """构造启动命令：冻结可执行文件直接带参数；源码运行时补上 main.py"""
    if getattr(sys, "frozen", False):
        return [sys.executable, *cmd_line.split()]
    return [sys.executable, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"), *cmd_line.split()]


def _app_working_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _unit_suffix(task_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", task_name).strip("-").lower()
    return sanitized or "aalc-task"


def _run_systemctl(*args: str) -> bool:
    try:
        result = subprocess.run(  # noqa: S603
            ["systemctl", "--user", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            log.debug(f"systemctl --user {' '.join(args)} 失败: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        log.debug(f"systemctl 调用异常: {e}")
        return False


class ScheduleHelper_Linux:
    """Schedule Helper 在 Linux 平台的实现（systemd 用户定时器 + XDG autostart）"""

    def register_daily_task(self, task_name: str, cmd_line: str, h: int, m: int):
        suffix = _unit_suffix(task_name)
        service_name = f"aalc-daily-{suffix}.service"
        timer_name = f"aalc-daily-{suffix}.timer"
        service_path = os.path.join(_SYSTEMD_USER_DIR, service_name)
        timer_path = os.path.join(_SYSTEMD_USER_DIR, timer_name)

        exec_args = _app_command_args(cmd_line)
        exec_str = " ".join(exec_args)

        service_content = "\n".join(
            [
                "[Unit]",
                f"Description={task_name}",
                "",
                "[Service]",
                "Type=oneshot",
                f"WorkingDirectory={_app_working_dir()}",
                f"ExecStart={exec_str}",
                "",
            ]
        )
        # OnCalendar 需要两位补零的 HH:MM
        calendar = f"*-*-* {h:02d}:{m:02d}:00"
        timer_content = "\n".join(
            [
                "[Unit]",
                f"Description={task_name} (timer)",
                "",
                "[Timer]",
                f"OnCalendar={calendar}",
                "Persistent=false",
                f"Unit={service_name}",
                "",
                "[Install]",
                "WantedBy=timers.target",
                "",
            ]
        )

        try:
            os.makedirs(_SYSTEMD_USER_DIR, exist_ok=True)
            with open(service_path, "w", encoding="utf-8") as f:
                f.write(service_content)
            with open(timer_path, "w", encoding="utf-8") as f:
                f.write(timer_content)
        except OSError as e:
            log.error(f"创建任务 {task_name} 失败: {e}")
            raise

        if not (_run_systemctl("daemon-reload") and _run_systemctl("enable", "--now", timer_name)):
            log.error(f"启用定时器 {timer_name} 失败")
            raise RuntimeError(f"启用 systemd 定时器失败: {timer_name}")
        log.info(f"创建每日任务成功，执行时间为每日{h:02d}:{m:02d}")

    def register_onstart_task(self, task_name: str, cmd_line: str):
        os.makedirs(_AUTOSTART_DIR, exist_ok=True)
        desktop_path = os.path.join(_AUTOSTART_DIR, f"{_unit_suffix(task_name)}.desktop")
        exec_str = " ".join(_app_command_args(cmd_line))
        content = "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                f"Name={task_name}",
                f"Exec={exec_str}",
                f"Path={_app_working_dir()}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        )
        try:
            with open(desktop_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            log.error(f"创建自启动项 {task_name} 失败: {e}")
            raise

    def unregister_task(self, task_name: str):
        suffix = _unit_suffix(task_name)
        # 每日任务：停用定时器并删除单元文件
        timer_name = f"aalc-daily-{suffix}.timer"
        service_name = f"aalc-daily-{suffix}.service"
        _run_systemctl("disable", "--now", timer_name)
        for file_name in (timer_name, service_name):
            path = os.path.join(_SYSTEMD_USER_DIR, file_name)
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError as e:
                    log.debug(f"删除单元文件失败 {path}: {e}")
        _run_systemctl("daemon-reload")

        # 登录自启动：删除 .desktop
        desktop_path = os.path.join(_AUTOSTART_DIR, f"{suffix}.desktop")
        if task_name == "AALC Autostart" and os.path.exists(desktop_path):
            try:
                os.unlink(desktop_path)
                log.debug(f"已移除启动项: {task_name}")
            except OSError as e:
                log.debug(f"通过移除自启动文件移除启动项失败: {e}")


class ScheduleHelper_Win32:
    """
    Schedule Helper 在 Win32 平台的实现
    """

    def __init__(self):
        import win32com.client
        from pywintypes import com_error

        self._com_error = com_error
        self.scheduler = win32com.client.Dispatch("Schedule.Service")
        self.scheduler.Connect()
        self.root = self.scheduler.GetFolder("\\")

    def register_daily_task(self, task_name: str, cmd_line: str, h: int, m: int):
        task_def = self.scheduler.NewTask(0)
        task_def.RegistrationInfo.Description = "AALC Daily Task"
        task_def.RegistrationInfo.Author = getpass.getuser()

        trigger = task_def.Triggers.Create(2)  # 每日触发器
        trigger.StartBoundary = datetime.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0).isoformat()
        trigger.DaysInterval = 1
        trigger.Enabled = True

        action = task_def.Actions.Create(0)
        action.Path = sys.executable
        action.Arguments = cmd_line
        action.WorkingDirectory = os.path.dirname(sys.executable)

        task_def.Principal.RunLevel = 1  # 管理员权限运行
        task_def.Principal.LogonType = 3
        task_def.Principal.Id = task_name
        task_def.Settings.Enabled = True
        task_def.Settings.Hidden = False
        task_def.Settings.ExecutionTimeLimit = "PT0S"
        task_def.Settings.DisallowStartIfOnBatteries = False
        task_def.Settings.StopIfGoingOnBatteries = False

        try:
            self.root.RegisterTaskDefinition(task_name, task_def, 6, None, None, 3)
            log.info(
                f"创建每日任务成功，执行时间为每日{h:02d}:{m:02d}"
            )
        except self._com_error as e:
            log.error(f"创建任务 {task_name} 失败")
            raise e

    def register_onstart_task(self, task_name: str, cmd_line: str):
        task_def = self.scheduler.NewTask(0)
        task_def.RegistrationInfo.Description = "AALC OnStart Task"
        task_def.RegistrationInfo.Author = getpass.getuser()

        trigger = task_def.Triggers.Create(9)  # 登录触发器
        trigger.Enabled = True

        action = task_def.Actions.Create(0)
        action.Path = sys.executable
        action.Arguments = cmd_line
        action.WorkingDirectory = os.path.dirname(sys.executable)

        task_def.Principal.RunLevel = 1  # 管理员权限运行
        task_def.Principal.LogonType = 3
        task_def.Principal.Id = task_name
        task_def.Settings.Enabled = True
        task_def.Settings.Hidden = False
        task_def.Settings.ExecutionTimeLimit = "PT0S"
        task_def.Settings.DisallowStartIfOnBatteries = False
        task_def.Settings.StopIfGoingOnBatteries = False

        try:
            self.root.RegisterTaskDefinition(task_name, task_def, 6, None, None, 3)
        except self._com_error as e:
            log.error(f"创建任务 {task_name} 失败")
            raise e

    def unregister_task(self, task_name: str):
        import winreg

        def unregister_onstart_task_registry(self, task_name):
            """
            删除自启动项
            """
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, task_name)
                winreg.CloseKey(key)
                log.debug(f"已移除启动项: {task_name}")
            except FileNotFoundError:
                pass  # 已经不存在了
            except Exception as e:
                log.debug(f"通过移除注册表移除启动项失败: {e}")

        try:
            if task_name == "AALC Autostart":
                unregister_onstart_task_registry(self, task_name)
            self.root.DeleteTask(task_name, 0)
        except self._com_error as e:
            log.warning(f"尝试删除不存在的任务 {task_name}")
            raise e
