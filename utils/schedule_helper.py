"""
utils.schedule_helper: 计划任务的帮助类的实现
"""

import datetime
import getpass
import os
import sys

import win32api
import win32com.client
from pywintypes import com_error

from module.logger import log


class ScheduleHelper:
    """
    计划任务的帮助类
    """

    def __init__(self):
        # 分离平台细节, 如果日后有跨平台需求能少写很多代码
        if os.name == "nt":
            self._impl = ScheduleHelper_Win32()
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


class ScheduleHelper_Win32:
    """
    Schedule Helper 在 Win32 平台的实现
    """

    def __init__(self):
        self.scheduler = win32com.client.Dispatch("Schedule.Service")
        self.scheduler.Connect()
        self.root = self.scheduler.GetFolder("\\")

    def register_daily_task(self, task_name: str, cmd_line: str, h: int, m: int):
        task_def = self.scheduler.NewTask(0)
        task_def.RegistrationInfo.Description = "AALC Daily Task"
        task_def.RegistrationInfo.Author = getpass.getuser()

        trigger = task_def.Triggers.Create(2)  # 每日触发器
        trigger.StartBoundary = (
            datetime.datetime.now()
            .replace(hour=h, minute=m, second=0, microsecond=0)
            .isoformat()
        )
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
        except com_error as e:
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
        except com_error as e:
            log.error(f"创建任务 {task_name} 失败")
            raise e

    def unregister_task(self, task_name: str):
        try:
            self.root.DeleteTask(task_name, 0)
        except com_error as e:
            log.warning(f"尝试删除不存在的任务 {task_name}")
            raise e
