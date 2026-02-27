"""
utils.schedule_helper: 计划任务的帮助类的实现
"""

import datetime
import getpass
import os
import sys
import winreg

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
        self._impl.register_onstart_task_registry(task_name, cmd_line)

    def unregister_task(self, task_name: str):
        """
        注销任务

        :param task_name: 任务名称
        :type task_name: str
        """
        self._impl.unregister_onstart_task_registry(task_name)
        log.info("移除每日任务成功")


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
        current_user = getpass.getuser()
        task_def.RegistrationInfo.Author = current_user

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

        task_def.Principal.RunLevel = 0  # 管理员权限运行
        task_def.Principal.LogonType = 2
        # task_def.Principal.Id = task_name
        task_def.Settings.Enabled = True
        task_def.Settings.Hidden = False
        task_def.Settings.ExecutionTimeLimit = "PT0S"
        task_def.Settings.DisallowStartIfOnBatteries = False
        task_def.Settings.StopIfGoingOnBatteries = False

        try:
            self.root.RegisterTaskDefinition(task_name, task_def, 6, None, None, 0)
            log.info(
                f"创建每日任务成功，执行时间为每日{h if len(str(h)) > 1 else '0' + str(h)}:{m if len(str(m)) > 1 else '0' + str(m)}"
            )
        except com_error as e:
            log.error(f"创建任务 {task_name} 失败")
            raise e

    def register_onstart_task_registry(self,task_name, executable_path=None):
        """
        使用注册表实现当前用户的开机自启动（无需管理员权限）
        """
        if executable_path is None:
            # 默认获取当前运行的 exe 或脚本路径
            executable_path = os.path.abspath(sys.argv[0])

        # 注册表路径：HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            # 打开注册表项
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            # 设置数值：任务名 = 程序路径
            winreg.SetValueEx(key, task_name, 0, winreg.REG_SZ, executable_path)
            winreg.CloseKey(key)
            log.info(f"成功添加启动项: {task_name}")
        except Exception as e:
            log.error(f"通过写入注册表添加启动项失败: {e}")

    def unregister_onstart_task_registry(self,task_name):
        """
        删除自启动项
        """
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, task_name)
            winreg.CloseKey(key)
            log.info(f"已移除启动项: {task_name}")
        except FileNotFoundError:
            pass  # 已经不存在了
        except Exception as e:
            log.error(f"通过移除注册表移除启动项失败: {e}")
